import json
from math import floor
import socket
from threading import Thread
import time
from algolab import API
from config import MY_API_KEY, MY_PASSWORD, MY_USERNAME
from ws import AlgoLabSocket
import re

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

def getTotalStockAmount(symbol):
    totalStock = '0'
    data = algo.GetInstantPosition()
    for item in data['content']:
        if item['code'] == symbol:
            totalStock = item['totalstock']
            break
    return float(totalStock)

def extract_reference_number(data):
    # Extracting the content string
    content = data.get('content', '')
    
    # Using regex to find the reference number
    match = re.search(r'Referans Numaranız: (\w+);', content)
    
    # Extracting the reference number if it matches
    if match:
        return match.group(1)
    else:
        return None

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
    SELL_INACTIVITY_DURATION = 120

    purchaseAmount = float(purchase_amount)
    sellSlippage = float(sell_slippage)
    sellPrice = 0
    stopLossPrice = 0
    buyStarted = False
    buyFinished = False
    soldStarted = False
    soldFinished = False
    buyId = ""
    sellId = ""
    buyLimitPrice = 0
    startingPrice = 0
    buyLot = 0
    sellLot = 0
    i = 0
    startTime = time.time()
    buyTime = time.time()
    logs = []

    print(f"{symbol}: {time.time()}")

    while soket.connected and (not soldFinished or time.time() - buyTime < 300):
        data = soket.recv()
        i += 1

        if data:
            try:
                msg = json.loads(data)
                if msg['Type'] == "T": 
                    if 'Date' in msg['Content']: logs.append(f"{msg['Content']['Date']}*{msg['Content']['Price']}") #ANALYSIS
                if soldFinished: 
                    continue #ANALYSIS

                if(msg['Type'] == 'O'): 
                    print(f"{symbol}: {msg}") #DEBUG

                if (msg['Content']['Symbol'] == symbol):
                    currentPrice = msg['Content']['Price']
    
                    if not buyStarted:
                        print(time.time())
                        buyLot = floor((purchaseAmount / 2) / currentPrice) #BUY_CALCULATION
                        buyLimitPrice = custom_round(currentPrice*BUY_SLIPPAGE) #BUY_CALCULATION
                        sellPrice = custom_round(currentPrice*sellSlippage) #BUY_CALCULATION
                        print(sellPrice)
                        startingPrice = currentPrice
                        print(f"{symbol}: Buying") #DEBUG
                        logs.append("BUY STARTED") #ANALYSIS
                        buyJson = algo.SendOrder(symbol=symbol, direction= 'Buy', pricetype= 'limit', price=str(buyLimitPrice), lot=str(buyLot) ,sms=False, email=False, subAccount="")
                        buyId = extract_reference_number(buyJson)
                        print(f"{buyJson} and {buyId}") #BUY
                        stopLossPrice = currentPrice * (1-STOP_LOSS_PERCENT)
                        buyStarted = True
                        buyTime = time.time() #ANALYSIS

                    elif not buyFinished:
                        print(f"{symbol}: Waiting for buy completion: {time.time() - buyTime}") #DEBUG

                        if msg['Type'] == 'O' and msg['Content']['Direction'] == 0 and msg['Content']['Status'] == 2:
                            sellLot = msg['Content']['Lot'] #SELL_CALCULATION
                            buyFinished = True
                            buyTime = time.time() #ANALYSIS
                            logs.append("BUY FINISHED") #ANALYSIS

                        elif (time.time() - buyTime > 10 or currentPrice > buyLimitPrice) and not buyFinished:
                            sellLot = getTotalStockAmount(symbol)
                            print(f"{symbol}: Total Lot= {sellLot}")
                            buyFinished = True
                            buyTime = time.time()
                            logs.append("BUY FORCE FINISHED") #ANALYSIS
                            algo.DeleteOrder(buyId,"")
                            soldFinished = sellLot == 0

                    elif buyFinished and not soldStarted:

                        print(f"{symbol}: Selling") #DEBUG
                        sellJson = algo.SendOrder(symbol=symbol, direction= 'Sell', pricetype= 'limit', price=str(sellPrice), lot=str(sellLot) ,sms=False, email=False, subAccount="")
                        sellId = extract_reference_number(sellJson)
                        soldStarted = True
                        logs.append("SELL STARTED") #ANALYSIS

                    elif not soldFinished:
                        if buyFinished: print(f"{symbol}:  {currentPrice} = {time.time() - buyTime}") #DEBUG
                        stockInactive = ((time.time() - buyTime > SELL_INACTIVITY_DURATION) and (currentPrice < startingPrice * 1.005)) #SELL_CALCULATION
                        stopLoss = currentPrice < stopLossPrice #SELL_CALCULATION

                        if msg['Type'] == 'O' and msg['Content']['Direction'] == 1 and msg['Content']['Status'] == 2:
                            soldFinished = True
                            logs.append("SELL FINISHED") #ANALYSIS
                        elif stockInactive or stopLoss:
                            limitPrice = custom_round(currentPrice-(step_calculator(currentPrice)*2))
                            print(f"{symbol}: Inactive Selling") #DEBUG
                            print(algo.ModifyOrder(sellId,str(limitPrice),"",False,""))
                        

            except Exception as e:
                print(e)
                break
    
    with open("analysis.txt", 'a') as file:
        list_as_string = str(logs)
        file.write(f"{symbol} - {startTime}: {list_as_string}\n")

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