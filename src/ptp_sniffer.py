import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import * 
import threading
import unittest
import os
import time
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
        Sniffer._packets = sniff(filter='ip', stop_filter=self._stopfilter)


    def _stopfilter(self, kill_packet):
        if kill_packet[IP].dst == '10.10.10.10':
            return True
        else:
            return False


    def stop(self):
        """Stop sniffer."""
        self._send_kill_packet()
	if not self.is_running():
            self._write_pcap()
        else:
            time.sleep(1)
            self.stop()


    def _write_pcap(self):
        """Write pcap file."""
        wrpcap(self._pcap_filename, self._packets)


    def pcap_filename(self):
        return self._pcap_filename 


    def _send_kill_packet(self):
        send(IP(dst='10.10.10.10'))


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
