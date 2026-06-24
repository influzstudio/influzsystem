#!/bin/bash
pip install -r requirements.txt
# Install Poppins font if not present
if [ ! -f "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf" ]; then
    mkdir -p /usr/share/fonts/truetype/google-fonts
    pip install requests
    python3 -c "
import requests, os
fonts = {
    'Poppins-Bold': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf',
    'Poppins-Regular': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf',
    'Poppins-Medium': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Medium.ttf',
    'Poppins-Light': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Light.ttf',
}
for name, url in fonts.items():
    r = requests.get(url, timeout=30)
    with open(f'/usr/share/fonts/truetype/google-fonts/{name}.ttf', 'wb') as f:
        f.write(r.content)
    print(f'Downloaded {name}')
"
fi
