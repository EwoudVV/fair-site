#!/usr/bin/env python3
"""Generate a QR code PNG for the given URL. Deps: python3-qrcode + PIL."""

import sys

import qrcode

def main():
    if len(sys.argv) != 3:
        print("usage: make_qr.py <url> <out.png>", file=sys.stderr)
        sys.exit(1)
    url, out = sys.argv[1], sys.argv[2]
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#14142b", back_color="#ffffff")
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
