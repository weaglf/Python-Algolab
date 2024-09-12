import json
from math import floor
import socket
from threading import Thread
import time
from algolab import API
from config import MY_API_KEY, MY_PASSWORD, MY_USERNAME
from ws import AlgoLabSocket
import re
import matriks

def step_calculator(value):
    if value > 2500:
        step = 2.50
    elif value > 1000:
        step = 1.00
    elif value > 500:
        step = 0.50
    elif value > 250:
        step = 0.25
    elif value > 100:
        step = 0.10
    elif value > 50:
        step = 0.05
    elif value > 20:
        step = 0.02
    elif value > 0:
        step = 0.01
    else:
        step = 0

    return step

def custom_round(value):
    step = step_calculator(value)

    # Calculate the nearest multiple of step that is greater than or equal to the value
    rounded_value = (value // step) * step
    if value % step != 0:
        rounded_value += step

    # Return the value rounded to two decimal places
    return round(rounded_value, 2)

def trailing_stop_loss(symbol,purchase_amount,sell_slippage):
    print(f"{symbol}: {time.time()}")
    soket = AlgoLabSocket(algo.api_key, algo.hash, "T")
    soket.connect()
    while not soket.connected:
        time.sleep(0.05)

    data = {"Type": "T", "Symbols": [symbol]}
    soket.send(data)

    BUY_SLIPPAGE = 1.005
    STOP_LOSS_PERCENT = 0.003
    SELL_INACTIVITY_DURATION = 180

    purchaseAmount = min(float(purchase_amount),210000)
    sellSlippage = float(sell_slippage)
    autoSellPrice = 0
    stopLossPrice = 0
    buyStarted = False
    buyFinished = False
    soldStarted = False
    soldFinished = False
    buyData = {}
    sellData = {}
    buyLimitPrice = 0
    startingPrice = 0
    sellLot = 0
    i = 0
    buyTime = time.time()
    m = matriks.MatriksIQ(brokage_id="41", account_id="0~930827", exchange_dd=4)

    print(f"{symbol}: {time.time()}")

    while soket.connected and not soldFinished:
        data = soket.recv()
        mdatas = m.recv()
        i += 1

        if mdatas:
            for mdata in mdatas:
                #print(mdata)

                if 'OrdStatus' in mdata:
                    print(mdata)
                    print("--------------")
                    if mdata['Symbol'] == symbol and mdata['OrdStatus'] == '0' and mdata['OrderSide'] == 0:
                        buyData = mdata
                    if mdata['Symbol'] == symbol and mdata['OrdStatus'] == '2' and mdata['OrderSide'] == 0:
                        sellLot = mdata['FilledQty']
                        buyFinished = True
                        buyTime = time.time()
                    if mdata['Symbol'] == symbol and mdata['OrdStatus'] == '4':
                        sellLot = m.ReceiveAmount(symbol)
                        soldStarted = False
                        soldFinished = sellLot == 0
                    if mdata['Symbol'] == symbol and mdata['OrdStatus'] == '0' and mdata['OrderSide'] == 1:
                        sellData = mdata
                    if mdata['Symbol'] == symbol and mdata['OrdStatus'] == '2' and mdata['OrderSide'] == 1:
                        soldFinished = True

        if data:
            try:
                msg = json.loads(data)

                if(msg['Type'] == 'O'): print(f"{symbol}: {msg}") 

                if (msg['Content']['Symbol'] == symbol):
                    currentPrice = msg['Content']['Price']
    
                    if not buyStarted:
                        print("Start Buying")
                        buyLot = floor(purchaseAmount / currentPrice) 
                        buyLimitPrice = custom_round(currentPrice*BUY_SLIPPAGE) 
                        autoSellPrice = custom_round(currentPrice*sellSlippage) 
                        stopLossPrice = currentPrice * (1-STOP_LOSS_PERCENT)
                        startingPrice = currentPrice
                        buyStarted = True
                        buyTime = time.time()
                        m.LimitBuy(symbol,buyLimitPrice,buyLot)

                    elif not buyFinished:
                        if time.time() - buyTime > 10 or currentPrice > buyLimitPrice:
                            print("Cancel Buy")
                            buyFinished = True
                            buyTime = time.time()
                            m.CustomOrder(buyData,4)
                            soldStarted = True

                    elif buyFinished and not soldStarted:
                        print("Start Selling")
                        m.LimitSell(symbol,autoSellPrice,sellLot)
                        soldStarted = True

                    elif not soldFinished:
                        stockInactive = ((time.time() - buyTime > SELL_INACTIVITY_DURATION) and (currentPrice < startingPrice * 1.005))
                        stopLoss = currentPrice < stopLossPrice
                        print(stockInactive)
                        print(stopLoss)
                        if stockInactive or stopLoss:
                            print("Sell Editing")
                            limitPrice = custom_round(currentPrice-(step_calculator(currentPrice)*2))
                            sellData['Price'] = limitPrice
                            m.CustomOrder(sellData,5)
                        

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
                    parts = decoded_message.split(':')
                    stockCode = parts[0] if len(parts) > 0 else "ABCDE"
                    purchaseAmount = parts[1] if len(parts) > 1 else "100"
                    sell_slippage = parts[2] if len(parts) > 2 else "1.01"
                    trail = Thread(target = trailing_stop_loss, args = (stockCode,purchaseAmount,sell_slippage,))
                    trail.start()
            finally:
                client_socket.close()
    except:
        print("Server is closing.")
    finally:
        server_socket.close()

algo = API(api_key=MY_API_KEY, username=MY_USERNAME, password=MY_PASSWORD, auto_login=True, keep_alive=True, verbose=True)
start_server()