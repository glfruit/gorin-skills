#!/usr/bin/env python3
"""
NeoBear - Next-Gen Bear Notes Link Tool
Convert %20 to + in Bear URLs for proper x-callback-url encoding

"NeoBear: Where old Bear links become new again." 🐻💫
"""

import sys
import argparse
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

__version__ = "2.0.0"
__author__ = "NeoBear Contributors"

# Try to import clipboard support
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class NeoBear:
    """Next-gen Bear URL converter."""
    
    BEAR_URL_PATTERN = re.compile(r'^bear://x-callback-url/')
    
    @staticmethod
    def is_bear_url(url):
        """Check if URL is a valid Bear URL."""
        return bool(NeoBear.BEAR_URL_PATTERN.match(url))
    
    @staticmethod
    def convert(url):
        """
        Convert %20 to + in Bear URL query parameters.
        
        Args:
            url (str): Bear URL with %20 encoding
            
        Returns:
            str: Bear URL with + encoding
        """
        if not isinstance(url, str):
            raise ValueError("URL must be a string")
        
        url = url.strip()
        
        if not NeoBear.is_bear_url(url):
            # Not a Bear URL, return as-is
            return url
        
        # Split base URL and query string
        parts = url.split('?', 1)
        if len(parts) == 1:
            # No query parameters
            return url
        
        base_url, query_string = parts
        
        # Replace %20 with + in query string
        fixed_query = query_string.replace('%20', '+')
        
        # Reconstruct URL
        return f"{base_url}?{fixed_query}"
    
    @staticmethod
    def convert_batch(urls):
        """
        Convert a list of URLs.
        
        Args:
            urls (list): List of URLs to convert
            
        Returns:
            list: List of converted URLs
        """
        return [NeoBear.convert(url) for url in urls]
    
    @staticmethod
    def from_clipboard():
        """
        Convert URL from clipboard.
        
        Returns:
            str: Converted URL
            
        Raises:
            RuntimeError: If clipboard is not available
        """
        if not CLIPBOARD_AVAILABLE:
            raise RuntimeError(
                "Clipboard support not available. "
                "Install pyperclip: pip install pyperclip"
            )
        
        url = pyperclip.paste()
        return NeoBear.convert(url)
    
    @staticmethod
    def to_clipboard(url):
        """
        Copy URL to clipboard.
        
        Args:
            url (str): URL to copy
            
        Raises:
            RuntimeError: If clipboard is not available
        """
        if not CLIPBOARD_AVAILABLE:
            raise RuntimeError(
                "Clipboard support not available. "
                "Install pyperclip: pip install pyperclip"
            )
        
        pyperclip.copy(url)
    
    @staticmethod
    def from_file(filepath):
        """
        Convert URLs from a file (one URL per line).
        
        Args:
            filepath (str): Path to file containing URLs
            
        Returns:
            list: List of converted URLs
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        return NeoBear.convert_batch(urls)
    
    @staticmethod
    def to_file(urls, filepath):
        """
        Save URLs to a file (one URL per line).
        
        Args:
            urls (list): List of URLs to save
            filepath (str): Path to output file
        """
        if isinstance(urls, str):
            urls = [urls]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + '\n')


def main():
    """Main entry point for NeoBear CLI."""
    parser = argparse.ArgumentParser(
        description='NeoBear - Next-gen Bear Notes link encoding tool',
        epilog='"NeoBear: Where old Bear links become new again." 🐻💫'
    )
    
    parser.add_argument(
        'url',
        nargs='?',
        help='Bear URL to convert'
    )
    
    parser.add_argument(
        '-c', '--clipboard',
        action='store_true',
        help='Convert URL from clipboard and copy result back'
    )
    
    parser.add_argument(
        '-f', '--file',
        metavar='FILE',
        help='Convert URLs from file (one per line)'
    )
    
    parser.add_argument(
        '-o', '--output',
        metavar='OUTPUT',
        help='Save output to file'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'NeoBear {__version__}'
    )
    
    args = parser.parse_args()
    
    try:
        # Determine input source
        if args.clipboard:
            # From clipboard
            if not CLIPBOARD_AVAILABLE:
                print("❌ Clipboard support not available", file=sys.stderr)
                print("Install with: pip install pyperclip", file=sys.stderr)
                sys.exit(1)
            
            result = NeoBear.from_clipboard()
            
            if args.output:
                NeoBear.to_file(result, args.output)
                print(f"✓ Saved to {args.output}")
            else:
                NeoBear.to_clipboard(result)
                print("✓ Converted and copied to clipboard!")
                print(f"Result: {result}")
        
        elif args.file:
            # From file
            results = NeoBear.from_file(args.file)
            
            if args.output:
                NeoBear.to_file(results, args.output)
                print(f"✓ Processed {len(results)} URLs")
                print(f"✓ Saved to {args.output}")
            else:
                for url in results:
                    print(url)
        
        elif args.url:
            # From command line argument
            result = NeoBear.convert(args.url)
            
            if args.output:
                NeoBear.to_file(result, args.output)
                print(f"✓ Saved to {args.output}")
            else:
                print(result)
        
        else:
            # No input provided, try stdin
            if not sys.stdin.isatty():
                # Reading from pipe
                urls = [line.strip() for line in sys.stdin if line.strip()]
                results = NeoBear.convert_batch(urls)
                
                if args.output:
                    NeoBear.to_file(results, args.output)
                    print(f"✓ Processed {len(results)} URLs", file=sys.stderr)
                    print(f"✓ Saved to {args.output}", file=sys.stderr)
                else:
                    for url in results:
                        print(url)
            else:
                # No input at all
                parser.print_help()
                sys.exit(1)
    
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
