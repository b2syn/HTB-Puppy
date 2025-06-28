import xml.etree.ElementTree as ET
tree = ET.parse('keepass_dump.xml')
root = tree.getroot()
for entry in root.iter('Entry'):
    username = None
    password = None
    for string in entry.findall('String'):
        key = string.find('Key').text
        value = string.find('Value').text
        if key == 'UserName':
            username = value
        elif key == 'Password':
            password = value
    if username or password:
        print(f"User: {username}, Password: {password}")
