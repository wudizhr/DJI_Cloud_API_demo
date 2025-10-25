# DJI_Cloud_API_demo

Terminal control example using DJI Cloud API.

## Setup

1. Install dependencies: `pip install -r ./requirements.txt`
2. Install docker and setup `emqx` (MQTT server)   --network
    - WSL:`docker run -d --name emqx --network host emqx:5.0.20`
    - other:`docker run -d --name emqx --network host -p 1883:1883 -p 8083:8083 -p 8084:8084 -p 8883:8883 -p 18083:18083 emqx:5.0.20`
    - open http://localhost:18083/ to setup admin account l: `admin` p: `public`
    - create user account (I am not sure whether it is needed, you can use admin account)
3. Connect your DJI Smart Controller to the same local network your PC is in (in case of laptop I recommend creating local hotspot).
4. Set env variable `HOST_ADDR`, `USERNAME`, `PASSWORD` to your IP which will be visible for controller and run `./cloud_api.http.py`
5. Set env variable `HOST_ADDR` and run `./test_mqtt.py`


### Conecting the controller

1. Open DJI Pilot App
2. Go to `Cloud Service` -> `Other platforms`
3. Write url `http://HOST_ADDR:5000/login` and connect
4. Press Login.
