from scapy.all import rdpcap, PacketList, Ether, IP, TCP, Raw
import hashlib
from ptp_network import Network
from ptp_constants import Constants
from ptp_session_pair import Session_Pair


class Session_Reassembler(object):
    """TCP-like pre-processing of sniffed packets from PCAP file, to be done
    before Application Layer protocol analysis can take place.

    Args:
        pcap_filename (str): name of existing PCAP file to pre-process.
    """


    def __init__(self, pcap_filename=None):
        self._pcap_filename = pcap_filename
        self._sessions_dict = None 
        self._session_pairs = None
        self._const = Constants()


    def get_session_pairs(self):
        """High level method calling all other methods required to pre-process packets.
        
        Returns: 
            dict of Session_Pair objects: The key is the 'quad' tuple (cli_ip, cli_pt,
            svr_ip, svr_pt).
        """ 

        session_pairs = {}
        sessions = self._get_sessions_dict()
        keys = sessions.keys()
        values = sessions.values()
        cli_ip = Network().get_cli_ip()

        for key in keys:
            # e.g. key = 'TCP 151.101.16.175:443 > 192.168.1.12:44071'
            #  opp_key = 'TCP 192.168.1.12:44071 > 151.101.16.175:443'
            prot, src, arrow, dst = key.split()
            src_ip, src_pt = src.split(':') 
            dst_ip, dst_pt = dst.split(':') 

            if dst_ip == self._const.KILL_PKT_IP: 
                continue

            opp_key = "%s %s:%s %s %s:%s" % \
                (prot, dst_ip, str(dst_pt), arrow, src_ip, str(src_pt))  
            session = sessions[key]

            if src_ip == cli_ip:
                quad = (src_ip, src_pt, dst_ip, dst_pt)
                if quad in session_pairs.keys(): 
                    # we must've hit opp_key earlier 
                    continue
                if opp_key in keys:
                    opp_session = sessions[opp_key]
                else:
                    opp_session = None
                session_pair = Session_Pair(session, opp_session)
                session_pairs[quad] = session_pair 
            else:
                quad = (dst_ip, dst_pt, src_ip, src_pt)
                if quad in session_pairs.keys(): 
                    # we must've hit opp_key earlier 
                    continue
                if opp_key in keys:
                    opp_session = sessions[opp_key]
                else:
                    opp_session = None
                session_pair = Session_Pair(opp_session, session)
                session_pairs[quad] = session_pair 

        self._session_pairs = session_pairs
        return self._session_pairs


    def _get_sessions_dict(self):
        """Extracts packets from PCAP file, splits into sessions, calls
        deduplication and sorting methods.

        Returns: 
            dict of PacketList objects
        """

        pkts = rdpcap(self._pcap_filename) 
        sessions = pkts.sessions()

        for key,session in sessions.iteritems():
            deduped_session = self._remove_duplicate_packets(session)
            sessions[key] = deduped_session
            self._sort_session_by_seq_no(session)

        self._sessions_dict = sessions
        return self._sessions_dict 


    def _sort_session_by_seq_no(self, session):
        """Sorts packets of session (PacketList) in-place by TCP sequence number,
        as packets are sometimes sniffed out of sequence number order. 
        We need them in that order to see e.g. TCP and SSL handshake completions. 
        Uses Python sort method, with TCP sequence number (from Scapy.Packet) as
        the key. Credit for sorting technique: Baggett M., IP Fragment Reassembly with
        Scapy.
        
        Args:
            session: Scapy.PacketList
        """
        def get_seq(pkt):
            return pkt[TCP].seq

        session.sort(key=get_seq)


    def _get_opposing_session_key(self, key):
        """To identify a session in a dict generated by Scapy.sessions(),
        Scapy uses a key which is a string of the form
        'protocol src_ip:src_pt > dst_ip:dst_pt' where the '>' indicates direction. 
        Given one such key, this method returns the key for the opposing session.

        Args:
            key: session identifier from a dict of PacketList objects

        Returns
            str: opposing key string 

        Examples:
            >>> _get_opposing_session_key("TCP 10.1.2.3:12345 > 192.168.1.1:9999")
            "TCP 192.168.1.1:9999 > 10.1.2.3:12345" 
        """
        prot, src, arrow, dst = key.split()
        src_ip, src_pt = src.split(':') 
        dst_ip, dst_pt = dst.split(':') 
        opp_key = "%s %s:%s %s %s:%s" % \
            (prot, dst_ip, str(dst_pt), arrow, src_ip, str(src_pt))  
        return opp_key


    def _remove_duplicate_packets(self, session):
        """Carries out partial de-duplication of Scapy.PacketList. 
        Packets are considered duplicate if they fall under one of these cases:
        both directions:
        * duplicate ack: no payload, flags=A, same seq and ack numbers.
        * duplicate data: flags=PA or A, same seq/ack/TCP chksum, same non-zero payload
        cli_to_svr:
        * duplicate syn: flags=S, same seq numbers 
        svr_to_cli:
        * duplicate synack: flags=SA, same seq/ack
        
        We hash the packets (credit: https://stackoverflow.com/a/3350656) depending on
        context. We'll need to make separate hash tables for each case to check.
        To make it easier to read, make a few reusable, function-like methods 
        first and use them to build up to the bigger algorithm.

        Args:
            session (Scapy.PacketList)
        
        Returns:
            Scapy.PacketList
        """

        def payload_len(pkt): return len(pkt[TCP].payload)
        def flags(pkt): return str(pkt[TCP].flags)
        def seq(pkt): return pkt[TCP].seq
        def ack(pkt): return pkt[TCP].ack
        def chksum(pkt): return pkt[TCP].chksum
        def md5(*args):
            str_args = map(str, args)
            return hashlib.md5("".join(str_args)).hexdigest()
        def is_ack(pkt):
            return flags(pkt) == 'A' and payload_len(pkt) == 0
        def hash_ack(pkt): return md5(seq(pkt)), ack(pkt) 
        def is_data(pkt):
            return payload_len(pkt) != 0 and (flags(pkt) == 'A' or flags(pkt) == 'PA')
        def hash_data(pkt): return md5(seq(pkt), ack(pkt), chksum(pkt), flags(pkt)) 
        def is_syn(pkt):
            return flags(pkt) == 'S' and ack(pkt) == 0
        def hash_syn(pkt): return md5(seq(pkt)) 
        def is_synack(pkt): return flags(pkt) == 'SA'
        def hash_synack(pkt): return md5(seq(pkt), ack(pkt)) 

        ack_pkts = {}
        data_pkts = {}
        syn_pkts = {}
        synack_pkts = {}

        deduped = [] 

        # if it's one of our cases and we haven't seen it then add to appropriate hash table and deduped.
        # if not one of our cases, just add it to deduped.
        # Can we safely assume no packet can fall under two cases?
        for pkt in session:
            if is_ack(pkt):
                if (hash_ack(pkt) not in ack_pkts.keys()):
                    deduped.append(pkt)
                    ack_pkts[hash_ack(pkt)] = pkt

            elif is_data(pkt):
                if (hash_data(pkt) not in data_pkts.keys()):
                    deduped.append(pkt)
                    data_pkts[hash_data(pkt)] = pkt

            elif is_syn(pkt):
                if (hash_syn(pkt) not in syn_pkts.keys()):
                    deduped.append(pkt)
                    syn_pkts[hash_syn(pkt)] = pkt

            elif is_synack(pkt):
                if (hash_synack(pkt) not in synack_pkts.keys()):
                    deduped.append(pkt)
                    synack_pkts[hash_synack(pkt)] = pkt

            else:
                deduped.append(pkt)

        return PacketList(deduped)
        
                
    def _print_sessions_dict_summary(self):
        for k,v in self._get_sessions_dict().iteritems():
            print k, "\n", v,"\n"


    def _print_session_summary(self, session):
        for pkt in session:
            print repr(pkt), "\n" 
