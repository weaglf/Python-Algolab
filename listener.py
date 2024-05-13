import json
from math import floor
import socket
from threading import Thread
import time
from algolab import API
from config import MY_API_KEY, MY_PASSWORD, MY_USERNAME
from ws import AlgoLabSocket


def trailing_stop_loss(symbol):
    soket = AlgoLabSocket(algo.api_key, algo.hash, "T")
    soket.connect()
    while not soket.connected:
        time.sleep(0.05)

    data = {"Type": "T", "Symbols": [symbol]}
    soket.send(data)

    percent = 0.003
    money = 80000

    top_price = 0
    sold = False
    buyStarted = False
    buyFinished = False
    buyLot = 0
    sellLot = 0

    i = 0
    a = 0
    while soket.connected and not sold:

        data = soket.recv()
        i += 1
        if data:
            try:
                msg = json.loads(data)
                
                if(msg['Type'] == 'O'): print(msg)
                elif not buyFinished and buyStarted: print("Waiting for buy")

                if (msg['Content']['Symbol'] == symbol):
                    currentPrice = msg['Content']['Price']
                    if(msg['Type'] != 'O'): top_price = max(currentPrice,top_price)
                    if buyFinished: print(f"{top_price} - {currentPrice} = {a}")
                    if not buyStarted:
                        buyLot = floor(money / currentPrice)
                        #print(d.SendOrder(symbol = symbol, direction = "BUY", pricetype = "Market", lot = lot, price=0.0, sms=True, email=False, subAccount=""))
                        print(algo.SendOrder(symbol=symbol, direction= 'Buy', pricetype= 'piyasa', price='', lot=str(buyLot) ,sms=False,email=False,subAccount=""))
                        buyStarted = True
                    elif msg['Type'] == 'O' and msg['Content']['Direction'] == 0:
                        sellLot += msg['Content']['Lot']
                        print(sellLot)
                        buyFinished = True
                    elif buyFinished and not sold:
                        #print(d.SendOrder(symbol = symbol, direction = "SELL", pricetype = "Market", lot = lot, price=0.0, sms=True, email=False, subAccount=""))
                        sellCondition = (currentPrice < top_price*(1-percent))
                        if sellCondition:
                            a += 1
                            if (a == 3):
                                print(algo.SendOrder(symbol=symbol, direction= 'Sell', pricetype= 'piyasa', price='', lot=str(sellLot) ,sms=False,email=False,subAccount=""))
                                sold = True
                        else:
                            a = 0

            except Exception as e:
                print(e)
                break
    
    soket.close()


def start_server(host='localhost', port=12345):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")    
    
    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connected by {addr}")
            try:
                while True:
                    # Receive data from the client
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    print(f"Received: {data.decode()}")
                    symbol = data.decode()
                    trail = Thread(target = trailing_stop_loss, args = (symbol,))
                    trail.start()
            finally:
                client_socket.close()
    except:
        print("Server is closing.")
    finally:
        server_socket.close()

algo = API(api_key=MY_API_KEY, username=MY_USERNAME, password=MY_PASSWORD, auto_login=True, verbose=True)
start_server()