code = open('capsule_template.txt', 'r', encoding='utf-8').read()
open('src/components/BeyondVistaarCapsule.jsx', 'w', encoding='utf-8').write(code)
print('Done')
