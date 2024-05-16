import json
from math import floor
import socket
from threading import Thread
import time
from algolab import API
from config import MY_API_KEY, MY_PASSWORD, MY_USERNAME
from ws import AlgoLabSocket


def trailing_stop_loss(symbol,purchase_amount):
    soket = AlgoLabSocket(algo.api_key, algo.hash, "T")
    soket.connect()
    while not soket.connected:
        time.sleep(0.05)

    data = {"Type": "T", "Symbols": [symbol]}
    soket.send(data)

    STOP_LOSS_PERCENT = 0.0035
    purchaseAmount = float(purchase_amount)
    
    buyStarted = False
    buyFinished = False
    soldStarted = False
    soldFinished = False
    top_price = 0
    buyLot = 0
    sellLot = 0
    i = 0
    a = 0

    while soket.connected and not soldFinished:

        data = soket.recv()
        i += 1
        if data:
            try:
                msg = json.loads(data)
                
                if(msg['Type'] == 'O'): print(f"{symbol}: {msg}")
                elif not buyFinished and buyStarted: print(f"{symbol}: Waiting for buy completion")

                if (msg['Content']['Symbol'] == symbol):

                    currentPrice = msg['Content']['Price']                    
                    if(msg['Type'] != 'O'): top_price = max(currentPrice,top_price)
                    
                    if buyFinished: print(f"{symbol}: {top_price} - {currentPrice} = {a}")

                    if not buyStarted:
                        buyLot = floor(purchaseAmount / currentPrice)
                        print(f"{symbol}: Buying")
                        print(algo.SendOrder(symbol=symbol, direction= 'Buy', pricetype= 'piyasa', price='', lot=str(buyLot) ,sms=False, email=False, subAccount=""))
                        buyStarted = True
                    elif msg['Type'] == 'O' and msg['Content']['Direction'] == 0 and msg['Content']['Status'] == 2:
                        sellLot += msg['Content']['Lot']
                        buyFinished = True
                    elif msg['Type'] == 'O' and msg['Content']['Direction'] == 1:
                        soldFinished = True
                    elif buyFinished and not soldStarted:
                        willSell = (currentPrice < top_price*(1-STOP_LOSS_PERCENT))
                        if willSell:
                            a += 1
                            if (a == 5):
                                print(f"{symbol}: Selling")
                                print(algo.SendOrder(symbol=symbol, direction= 'Sell', pricetype= 'piyasa', price='', lot=str(sellLot) ,sms=False, email=False, subAccount=""))
                                soldStarted = True
                        else:
                            a = 0

            except Exception as e:
                print(e)
                break
    
    soket.close()
    print(f"{symbol}: closed!")

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
                    decoded_message = data.decode()
                    print(f"Received: {decoded_message}")
                    stockCode, purchaseAmount = decoded_message.split(':')
                    trail = Thread(target = trailing_stop_loss, args = (stockCode,purchaseAmount,))
                    trail.start()
            finally:
                client_socket.close()
    except:
        print("Server is closing.")
    finally:
        server_socket.close()

algo = API(api_key=MY_API_KEY, username=MY_USERNAME, password=MY_PASSWORD, auto_login=True, keep_alive=True, verbose=True)
start_server()