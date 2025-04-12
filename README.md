# CTF-Flag-Submitter
Submitter di Flags per prove A/D

Ad ogni prova vanno eseguite le seguenti modifiche:
  - self.TEAM_TOKEN

Per poter mandare le flag scrivere su un terminale il seguente comando (Da modificare in loco):
  - curl -X POST http://10.81.63.9:5000/submit -d "flag=080A02AF0J07UMOPHNE00KJ48KAE28C="

Al momento questo comando consente di inviare una flag alla volta.
