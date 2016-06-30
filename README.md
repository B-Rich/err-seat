# err-seat
Seat Api Interface for errbot, reports starbases (out of fuel, silo full, siphon, reinforced). Ability to search for pocos/posses, offline posses, posses that run out of fuel in x hours.

## Installation
You need errbot and eveseat please see the following links for setting that up:   
*  http://errbot.io
*  http://seat-docs.readthedocs.io/en/latest/

## Connecting / Configuration
Under https://yourseatdomain.com/api-admin add the ip of your errbot instance.
In the seat.py you need to set the api url and the token you just generated plus the additional settings.
Example:
```
!plugin config seat
{'FUEL_THRESHOLD': '12',
 'REPORT_POS_CHAN': '#starbases',
 'REPORT_REINF_CHANNEL': '#fleetcommand',
 'SEAT_TOKEN': 'JSjklasjdklasdljkljd2323',
 'SEAT_URL': 'https://seat.mydomain.com/api/v1'}
```

## Help Call Example
seat

Seat API to errbot interface

- !poco find - Finds all pocos in given <system>, Usage !poco find <system>
- !poco refetch - Refetches seat poco API data
- !pos find - Finds all towers in given <system>, Usage !pos find <system>
- !pos offline - Finds all offline towers, Usage: !pos offline
- !pos oof - Finds all towers that will be running out of fuel in the given timeframe, Usa...
- !pos refetch - Refetches seat pos API data
- !pos silencefuel - Silences the out of fuel notification for a tower: Usage !pos silencefuel <Po...
- !pos silencefull - Silences notification if a silo/coupling array is full: Usage !pos silenceful...
- !pos silencesiphon - Silences the siphon notification for a tower: Usage !pos silencesiphon <PosID>
plus a few admin commands which are documented in the code itself.

## misc
only tested against discord.py with errbot 4.1.3+.  
Keep in mind that eve api and seat api data is delayed.

## Contact
If you got questions catch me on gitter https://gitter.im/errbotio/errbot
