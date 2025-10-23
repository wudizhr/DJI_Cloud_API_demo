import time
import json

class Ser_puberlisher:
    def __init__(self, gateway_sn, client):
        self.gateway_sn = gateway_sn
        self.topic = f"thing/product/{self.gateway_sn}/services"
        self.client = client
        self.seq = 0
        self.is_beat = True
        self.freq = 1.0  # 心跳频率，单位Hz

    def publish_heartbeat(self):
        if self.is_beat:
            heartbeat_msg = {
                "data": {"timestamp": int(time.time() * 1000)},
                "method": "heart_beat",
                "seq": self.seq,
            }
            self.client.publish(f"thing/product/{self.gateway_sn}/drc/down", payload=json.dumps(heartbeat_msg), qos=1)
            self.seq += 1