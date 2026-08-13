#!/usr/bin/env python3
"""Generate a self-contained printable table sign (HTML) with the QR code."""

import base64
import sys
from io import BytesIO

import qrcode

def main():
    if len(sys.argv) != 3:
        print("usage: make_sign.py <url> <out.html>", file=sys.stderr)
        sys.exit(1)
    url, out = sys.argv[1], sys.argv[2]

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=16,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#14142b", back_color="#ffffff")
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Scan me — Ellie Makes</title>
<style>
  @page {{ size: letter portrait; margin: 0; }}
  body {{ margin: 0; font-family: -apple-system, system-ui, sans-serif; display: grid; place-items: center; min-height: 100vh; background: #14142b; }}
  .sign {{ width: 100%; max-width: 720px; background: #fdfbf5; border-radius: 28px; margin: 18px; box-shadow: 0 12px 0 rgba(0,0,0,.35); overflow: hidden; }}
  .head {{ background: #ffd166; padding: 18px 26px; font-weight: 800; font-size: 15px; letter-spacing: .02em; }}
  .body {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; padding: 26px; align-items: center; }}
  .qr img {{ width: 100%; border-radius: 14px; }}
  h1 {{ font-size: 34px; line-height: 1.05; margin: 0 0 8px; letter-spacing: -.02em; }}
  .sub {{ font-size: 17px; color: #4b4b63; margin: 0 0 14px; }}
  .btns {{ display: grid; gap: 8px; }}
  .btn {{ display: block; text-align: center; font-weight: 750; padding: 11px; border-radius: 12px; border: 2px solid #14142b; text-decoration: none; color: #14142b; background: #fff; font-size: 15px; }}
  .btn.primary {{ background: #ffd166; }}
  .btn.dark {{ background: #14142b; color: #fff; }}
  .url {{ font-family: ui-monospace, monospace; font-size: 12px; color: #4b4b63; word-break: break-all; margin: 14px 0 0; }}
  .foot {{ border-top: 2px solid #dcd6c8; padding: 12px 26px; font-size: 13px; color: #4b4b63; }}
</style>
</head>
<body>
  <div class="sign">
    <div class="head">ELLIE MAKES · scan me at the fair</div>
    <div class="body">
      <div>
        <h1>Robots, drawing machines &amp; electronics lessons</h1>
        <p class="sub">Scan the code to see what's on the table — and sign up for a hands-on lesson.</p>
        <div class="btns">
          <a class="btn primary" href="{url}">Open website</a>
          <a class="btn dark" href="{url}#signup">Book a lesson</a>
        </div>
        <p class="url">{url}</p>
      </div>
      <div class="qr"><img src="data:image/bmp;base64,{b64}" alt="QR code"></div>
    </div>
    <div class="foot">Questions? Ask Ellie at the booth. Every scan helps — thank you!</div>
  </div>
</body>
</html>
"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(out)


if __name__ == "__main__":
    main()
