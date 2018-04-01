import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import Ether, IP, TCP, sendp
import threading
import unittest
import os
import time
import pcapy
from socket import ntohs
from struct import unpack
#from import ptp_mock_target_device *

class Sniffer:

    _packets = None
    _sniffer_thread = None

    def __init__(self, pcap_filename='sniffed.pcap'):
        self._pcap_filename = pcap_filename 
        Sniffer._sniffer_thread = threading.Thread(target=self._run_sniffer_thread)
        Sniffer._sniffer_thread.daemon = True

    def start(self):
        """Start sniffer."""
        Sniffer._sniffer_thread.start()
        #return self.is_running()



    def _run_sniffer_thread(self):
        dev = 'enp0s3' 
        cap = pcapy.open_live(dev , 65536 , 1 , 0)
	stop_eth_addr = '00:00:00:03:02:01'
	bpf_filter = "tcp or ether dst " + stop_eth_addr
	cap.setfilter(bpf_filter)
	dumper = cap.dump_open(self._pcap_filename)

	while(True):
	    packet_hdr, packet_body = cap.next()
	    dumper.dump(packet_hdr,packet_body)
	    if self._is_stop_packet(packet_body, stop_eth_addr):
		break

	del dumper

    '''credit: binary tides'''
    def _eth_addr(self, a):
	b = "%.2x:%.2x:%.2x:%.2x:%.2x:%.2x" % (ord(a[0]) , ord(a[1]) , ord(a[2]), ord(a[3]), ord(a[4]) , ord(a[5]))
	return b

    '''credit: binary tides'''
    def _is_stop_packet(self, packet_body, stop_eth_addr):
	eth_header_length = 14
	eth_header = packet_body[:eth_header_length]
	eth = unpack('!6s6sH' , eth_header)
	eth_protocol = ntohs(eth[2])
	eth_header_bytes = packet_body[0:6]
	eth_addr_str = self._eth_addr(eth_header_bytes)
	if eth_addr_str == stop_eth_addr:
	    # print 'Stop packet received'
	    return True
	return False


    def stop(self):
        """Stop sniffer."""
        self._send_kill_packet()
	if self.is_running():
            time.sleep(1)
            self.stop()


    def pcap_filename(self):
        return self._pcap_filename 

    def _send_kill_packet(self):
	kill_packet = Ether(dst='00:00:00:03:02:01')/IP(dst='10.11.12.13')/TCP()
	sendp(kill_packet)

    def is_running(self):
        return Sniffer._sniffer_thread.isAlive()
        

    def pcap_file_written(self):
        return False


class TestSniffer(unittest.TestCase):

    def setUp(self):
        pcap_filename = 'sniffed_TEST.pcap'
        self.sniffer = Sniffer(pcap_filename=pcap_filename)

    def tearDown(self):
        self.sniffer.stop()
        
    def test_no_sniffer_is_not_running_before_starting_it(self):
        self.assertFalse(self.is_running())

    def test_start_starts_sniffer(self):
        self.sniffer.start()
        self.assertTrue(self.is_running())

    def test_stop_stops_sniffer(self):
        self.sniffer.start()
        #td = ptp_mock_target_device.MockTD()
        #td.send_packet()
        self.sniffer.stop()
        self.assertFalse(self.is_running())
    
    def test_write_pcap_writes_file_if_sniffer_has_finished(self):
        self.sniffer.start()
        self.sniffer.stop()
        self._write_pcap()
        self.assertTrue(self.pcap_file_written())

    def test_write_pcap_does_not_write_file_if_sniffer_has_not_finished(self):
        self.sniffer.start()
        self._write_pcap()
        self.assertFalse(self.pcap_file_written())


if __name__ == '__main__':
    unittest.main()
