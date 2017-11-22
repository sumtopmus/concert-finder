# ConcertsFinder
Python script to look for the concerts of favorite bands around.

On Linux preinstall this for `Pillow`:
```bash
sudo apt-get install libffi-dev libjpeg-dev
```

Install necessary dependencies:
```bash
pip3 install requests pandas geopy jinja2 weasyprint
```

To use, create `data` folder and add `*.txt` files there with one band name per line. Then call `src/loader.py`.
