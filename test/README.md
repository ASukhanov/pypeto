Configuration files for testing pypet.<br>

These tests are working with two LiteServers. One is serving UDP port ```localhost:9701```, another is serving port 9701 of the hosts IP address. 
The liteServer module can be installed using ```pip install liteserver```.<br>
The servers should be started using following commands:<br>
```
python -m liteserver.device.litePeakSimulator -ilocalhost -p9701
python -m liteserver.device.litePeakSimulator -p9701
python -m liteserver.device.liteScaler -ilocalhost -p9700
```
Testing commands:<br>
```
python -m pypeto -c test -f peakSimLocal
python -m pypeto -c test -f peakSimLocal peakSimGlobal
python -m pypeto -c test -f peakSimLocal peakSimGlobal lclScaler
python -m pypeto -c test
python -m pypeto -aLITE 'localhost;9701:dev1'
python -m pypeto -c test -f simScopePVA
```

