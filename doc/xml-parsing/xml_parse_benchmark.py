#! /usr/bin/env python3

import sys
import time
from xml.dom import minidom
import xml.etree.ElementTree as ET

def print_usage_and_bail():
    print(f"Usage: python {sys.argv[0]} <path_to_xml_file>")
    sys.exit(1)


def benchmark_minidom(filename):
    start = time.time()
    dom = minidom.parse(filename)
    elapsed = time.time() - start
    print(f"minidom: {elapsed:.2f} seconds")
    return dom


def benchmark_elementtree(filename):
    start = time.time()
    tree = ET.parse(filename)
    root = tree.getroot()
    elapsed = time.time() - start
    print(f"ElementTree: {elapsed:.2f} seconds")
    return tree


def benchmark_lxml(filename):
    try:
        from lxml import etree as lxml_etree
        lxml_available = True
    except ImportError:
        lxml_available = False
        print("lxml not installed — skipping lxml benchmark")

    if not lxml_available:
        return None
    start = time.time()
    tree = lxml_etree.parse(filename)
    root = tree.getroot()
    elapsed = time.time() - start
    print(f"lxml: {elapsed:.2f} seconds")
    return tree
    

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_usage_and_bail()
        
    filename = sys.argv[1]
    
    print(f"Benchmarking parsing of {filename}...")
    benchmark_minidom(filename)
    benchmark_elementtree(filename)
    benchmark_lxml(filename)

