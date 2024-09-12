import socket
import datetime
import json

IP = "127.0.0.1" # Server IP
PORT = 18890 # Port
TIME_OUT = 1 # seconds

# API COMMANDS
CMD_ListAccounts = 0
CMD_ListPositions = 1
CMD_ListOrders = 2
CMD_NewOrder = 3
CMD_CancelOrder = 4
CMD_EditOrder = 5
CMD_SendKeepAlive = 6
CMD_SendAccountInformationRequest = 7
CMD_RequestFilledOrders = 8
CMD_RequestCanceledOrders = 9
CMD_ChangeLoggingMode = 10
CMD_ChangeBroadcastMode = 11

# Exchange IDs
EX_ISE = 4 # Borsa İstanbul Spot Piyasası
EX_ISE_INDEX = 27 # Borsa İstanbul Endeksi
EX_FX = 3 # Forex
EX_VIOP = 9 # Vadeli İşlemler ve Opsiyon Piyasası
EX_OTHER = 0 # Diğer
EX_CRYPTO = 65 # Kripto Para Piyasası
EX_BINANCE_USDT_FUTURES = 10001 # Binance Vadeli İşlemler Piyasası

# Order Status
STATUS_New = "0" # Bekliyor
STATUS_PartiallyFilled = "1" # Parçalı Gerçekleşme
STATUS_Filled = "2" # Gerçekleşti
STATUS_Canceled = "4" # İptal
STATUS_Replaced = "5" # Düzeltildi
STATUS_PendingCancel = "6" # İptal Bekliyor
STATUS_Stopped = "7" # Durduruldu
STATUS_Rejected = "8" # Reddedildi
STATUS_Suspended = "9" # Beklemeye Alindi
STATUS_PendingNew = "A" # İletilmeyi Bekliyor
STATUS_Expired = "C" # Zaman Aşımı
STATUS_AcceptedForBidding = "D" # Düzeltme Bekleniyor
STATUS_PendingReplace = "E" # Düzeltme İsteği Gönderildi Cevap Bekleniyor
STATUS_RemoveFromList = "Z" # Silinmiş Emir

# Time In Force TIF
TIF_Day = "0" # Günlük
TIF_GoodTillCancel = "1" # İptale kadar geçerli
TIF_AtTheOpening = "2" # Açılış seanslık geçerli işlem tipi
TIF_ImmediateOrCancel = "3" # Kalanı iptal et
TIF_FillOrKill = "4" # Gerçekleşmezse iptal et
TIF_GoodTillDate = "6" # Tarihli süre tipi
TIF_AtTheClose = "7" # Kapanış seanslık geçerli işlem tipi
TIF_Seans = "8" # Seanslık geçerli işlem tipi
TIF_AtCrossing = "9" # Dengeleyici emirler için eşleşme seansını ifade eder

# Transaction Types
TT_Normal = "1" # Normal Emir
TT_ShortDefault = "2" # Açığa Satış Emri
TT_ShortDaily = "3" # Gün İçi Kapanacak Açığa Satış Emri
TT_Virman = "4" # Virman Emri
TT_Credit = "5" # Kredili İşlem
TT_CloseShort = "6" # Açığa Satışı Kapama Emri

# Side
SIDE_BUY = 0 # Alış yönlü emir
SIDE_SELL = 1 # Satış yönlü emir

# Order Side
ORDER_SIDE_BUY = 1 # Alış yönlü emir
ORDER_SIDE_SELL = 2 # Satış yönlü emir

# Order Types
ORDER_TYPE_MARKET = "1" # Piyasa emri
ORDER_TYPE_LIMIT = "2" # Limit emir
ORDER_TYPE_MARKET_LIMIT = "R" # Limit emir

class MatriksIQ:
    def __init__(self, brokage_id: str, account_id: str, exchange_dd: int):
        self.brokage_id = brokage_id
        self.account_id = account_id
        self.exchange_dd = exchange_dd
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(TIME_OUT)
        try:
            self.client.connect((IP, PORT))
            # Activate JSON
            self.client.send("SetMessageType0".encode())
        except socket.timeout:
            print("Connection timeout")

    def send(self, payload):
        json_str = json.dumps(payload) + chr(11)
        d = json_str.encode()
        try:
            s = self.client.send(d)
        except socket.timeout:
            print("Timeout")
        return s

    def recv(self):
        d = None
        try:
            r = self.client.recv(5001)
            raw_data = r.decode().strip()
            
            # Attempt to load multiple JSON objects from raw_data
            json_objects = []
            decoder = json.JSONDecoder()
            pos = 0
            while pos < len(raw_data):
                raw_data = raw_data.strip()  # Strip any whitespace
                try:
                    if not raw_data[pos:]:
                        break
                    obj, index = decoder.raw_decode(raw_data[pos:])
                    json_objects.append(obj)
                    pos += index
                    # Skip any remaining whitespace or newlines between JSON objects
                    while pos < len(raw_data) and raw_data[pos].isspace():
                        pos += 1
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e} at position {pos}")
                    break  # Break on error, you might want to handle differently

            d = json_objects
        except socket.timeout:
            print("Timeout")
        except Exception as e:
            print(f"Exception: {e}")

        # Return the first element of d if it exists
        if d:
            return d
        return None


    ### API Functions ###

    def ListAccounts(self):
        payLoad = {
            "ApiCommands": CMD_ListAccounts
        }
        return self.send(payLoad)

    def SetPayload(self, api_commands, **kwargs):
        payLoad = {
            "BrokageId": self.brokage_id,
            "AccountId": self.account_id,
            "ExchangeId": self.exchange_dd,
            "ApiCommands": api_commands
        }
        for q in kwargs:
            payLoad[q] = kwargs[q]
        return payLoad

    def ListPositions(self, **kwargs):
        payload = self.SetPayload(CMD_ListPositions, **kwargs)
        return self.send(payload)
    
    def ReceiveAmount(self, symbol):
        self.ListPositions()
        r = self.recv()
        data = []
        if r and 'PositionResponseList' in r[0]:
            data = r[0]['PositionResponseList']
        return next((item['QtyAvailable'] for item in data if item['Symbol'] == symbol), 0)
        
    def ListOrders(self, **kwargs):
        payload = self.SetPayload(CMD_ListOrders, **kwargs)
        return self.send(payload)

    def RequestFilledOrders(self, **kwargs):
        payload = self.SetPayload(CMD_RequestFilledOrders, **kwargs)
        return self.send(payload)

    def RequestCanceleddOrders(self, **kwargs):
        payload = self.SetPayload(CMD_RequestCanceledOrders, **kwargs)
        return self.send(payload)

    def SendAccountInformationRequest(self, **kwargs):
        payload = self.SetPayload(CMD_SendAccountInformationRequest, **kwargs)
        return self.send(payload)

    def SendNewOrder(self, symbol: str, price: float, lot: float, order_type: str,
                     side: int, tif: str, transaction_type: str):
        payload = {
            "ApiCommands": CMD_NewOrder,
            "AccountId": self.account_id,
            "BrokageId": self.brokage_id,
            "Symbol": symbol,
            "Price": price,
            "Quantity": lot,
            "LeavesQty": lot,
            "OrderId2": lot,
            "OrderQty": lot,
            "OrderSide": side,
            "OrderType": order_type,
            "TimeInForce": tif,
            "TransactionType": transaction_type,
            "ClientOrderId": self.new_order_id
        }
        return self.send(payload)

    def SendKeepAlive(self):
        payLoad = {
            "KeepAliveDate": self.now,
            "ApiCommands": CMD_SendKeepAlive
        }
        return self.send(payLoad)

    # ALIAS
    def MarketBuy(self, symbol, lot, tif=TIF_Day, transaction_type=TT_Normal):
        r = self.SendNewOrder(symbol=symbol, price=0.0, lot=lot, order_type=ORDER_TYPE_MARKET, side=SIDE_BUY, tif=tif, transaction_type=transaction_type)
        return r

    def MarketSell(self, symbol, lot, tif=TIF_Day, transaction_type=TT_Normal):
        r = self.SendNewOrder(symbol=symbol, price=0.0, lot=lot, order_type=ORDER_TYPE_MARKET, side=SIDE_SELL, tif=tif, transaction_type=transaction_type)
        return r

    def LimitBuy(self, symbol, price, lot, tif=TIF_Day, transaction_type=TT_Normal):
        r = self.SendNewOrder(symbol, price, lot, order_type=ORDER_TYPE_LIMIT, side=ORDER_SIDE_BUY, tif=tif, transaction_type=transaction_type)
        return r

    def LimitSell(self, symbol, price, lot, tif=TIF_Day, transaction_type=TT_Normal):
        r = self.SendNewOrder(symbol, price, lot, order_type=ORDER_TYPE_LIMIT, side=ORDER_SIDE_SELL, tif=tif, transaction_type=transaction_type)
        return r
    
    def CustomOrder(self, data, commandNo):
        payload = {
            "OrderSide": data['OrderSide'],
            "OrderID": data['OrderID'],
            "OrderID2": data['OrderID2'],
            "OrderQty": data['OrderQty'],
            "OrdStatus": data['OrdStatus'],
            "LeavesQty": data['LeavesQty'],
            "FilledQty": data['FilledQty'],
            "AvgPx": data['AvgPx'],
            "TradeDate": data['TradeDate'],
            "TransactTime": data['TransactTime'],
            "StopPx": data['StopPx'],
            "Explanation": data['Explanation'],
            "ExpireDate": data['ExpireDate'],
            "Symbol": data['Symbol'],
            "Price": data['Price'],
            "Quantity": data['Quantity'],
            "IncludeAfterSession": data['IncludeAfterSession'],
            "TimeInForce": data['TimeInForce'],
            "OrderType": data['OrderType'],
            "TransactionType": data['TransactionType'],
            "AccountId": self.account_id,
            "BrokageId": self.brokage_id,
            "ApiCommands": commandNo
        }
        return self.send(payload)
    

    now = property(lambda self: f"{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z')}")
    new_order_id = property(lambda self: f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f%z')}")