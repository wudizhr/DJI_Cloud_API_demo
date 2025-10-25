# DJI_Cloud_API_demo

Terminal control example using DJI Cloud API.
reference project https://github.com/pktiuk/DJI_Cloud_API_minimal.git Thank you for his sharing!

## Setup

1. Install dependencies: `pip install -r ./requirements.txt`
2. Install docker and setup `emqx` (MQTT server)   --network
    - WSL:`docker run -d --name emqx --network host emqx:5.0.20`
    - Other:`docker run -d --name emqx --network host -p 1883:1883 -p 8083:8083 -p 8084:8084 -p 8883:8883 -p 18083:18083 emqx:5.0.20`
    - open http://localhost:18083/ to setup admin account l: `admin` p: `public`
    - create user account (I am not sure whether it is needed, you can use admin account)
    - can run `source restart_docker.sh` to restart emqx MQTT server
3. Connect your DJI Smart Controller to the same local network your PC is in (in case of laptop I recommend creating local hotspot).
4. Set env variable `HOST_ADDR`, `USERNAME`, `PASSWORD` in `config.sh` and run `source config.sh` to application them
5. Set host in `couldhtml/login.html` and run `./cloud_api_http.py` to start http server
6. Run `./multi_client_mqtt.py` to activate the multi machine control terminal

### Conecting the controller

1. Open DJI Pilot App
2. Go to `Cloud Service` -> `Other platforms`
3. Write url `http://HOST_ADDR:5500/login` and connect
4. Press Login.
