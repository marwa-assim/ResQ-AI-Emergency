import re, subprocess
html = open('templates/dashboard.html', encoding='utf-8').read()
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
for i, s in enumerate(scripts):
    open(f'temp_{i}.js', 'w', encoding='utf-8').write(s)
    result = subprocess.run(['node', '-c', f'temp_{i}.js'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f'Script {i} syntax error:\n{result.stderr}')
    else:
        print(f'Script {i} OK')
