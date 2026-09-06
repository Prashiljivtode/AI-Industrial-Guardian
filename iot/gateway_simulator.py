"""Send simulated telemetry to the FastAPI IoT endpoint.
Run the backend first, then: python iot/gateway_simulator.py --machine M1 --seconds 5
"""
import argparse, random, time, requests

p=argparse.ArgumentParser(); p.add_argument('--url',default='http://127.0.0.1:8000'); p.add_argument('--machine',default='M1'); p.add_argument('--seconds',type=int,default=5); p.add_argument('--risk-mode',action='store_true'); args=p.parse_args()
for i in range(max(1,args.seconds)):
    if args.risk_mode:
        payload={'temp':random.uniform(92,108),'vibration':random.uniform(1.1,1.8),'pressure':random.uniform(42,54)}
    else:
        payload={'temp':random.uniform(55,82),'vibration':random.uniform(.18,.75),'pressure':random.uniform(28,42)}
    r=requests.post(f'{args.url}/api/v1/telemetry/{args.machine}',json=payload,timeout=5)
    print(r.status_code, r.json())
    time.sleep(1)
