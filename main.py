import os
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from Stock import FrequencyEnum, StockData, StockLine
import pandas as pd
import asyncio

app = FastAPI()
symbols = set(f.split('.')[0] for f in os.listdir("./Stocks"))

@app.get("/")
def query_main(symbol : str = "", frequency : FrequencyEnum = FrequencyEnum.daily) -> StockData:
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol not specified")
    elif symbol.lower() not in symbols:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    df = pd.read_csv(f"./Stocks/{symbol.lower()}.us.txt")   
    df['Date'] = pd.to_datetime(df['Date'])
    
    agg_dict = {
        "Date": "first",
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
        "OpenInt": "sum"
    }
    
    if frequency == FrequencyEnum.weekly:
        df = df.resample("W", on='Date').agg(agg_dict)
    elif frequency == FrequencyEnum.monthly:
        df = df.resample("M", on='Date').agg(agg_dict)
    elif frequency == FrequencyEnum.yearly:
        df = df.resample("Y", on='Date').agg(agg_dict)
    
    return StockData(data=[
        StockLine(
            Date=row["Date"].to_pydatetime(), 
            Open=row["Open"], 
            High=row["High"], 
            Low=row["Low"], 
            Close=row["Close"], 
            Volume=row["Volume"], 
            OpenInt=row["OpenInt"]) 
        for _, row in df.iterrows()])
    
async def stream_symbol_data(websocket: WebSocket, symbol: str):
    if symbol.lower() not in symbols:
        await websocket.send_json({"error": f"Symbol {symbol} not found."})
        return

    file_path = f"./Stocks/{symbol.lower()}.us.txt"
    if not os.path.isfile(file_path):
        await websocket.send_json({"error": f"No file for symbol {symbol}."})
        return

    df = pd.read_csv(file_path)
    df["Date"] = pd.to_datetime(df["Date"])

    for _, row in df.iterrows():
        payload = {
            "symbol": symbol,
            "Date": row["Date"].to_pydatetime().isoformat(),
            "Open": float(row["Open"]),
            "High": float(row["High"]),
            "Low": float(row["Low"]),
            "Close": float(row["Close"]),
            "Volume": int(row["Volume"]),
            "OpenInt": int(row["OpenInt"]),
        }
        await websocket.send_json(payload)
        await asyncio.sleep(0.5)

# a temperory solution to stream multiple stocks data until creating a timeseries database.
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, symbols: str = Query(...)):
    await websocket.accept()
    print(symbols)
    symbols_requested = [sym.lower() for sym in symbols.split(",")]
    
    tasks = [
        asyncio.create_task(stream_symbol_data(websocket, sym))
        for sym in symbols_requested
    ]

    try:
        await asyncio.gather(*tasks)
    except WebSocketDisconnect:
        print("Client disconnected.")
    finally:
        await websocket.close()