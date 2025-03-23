import json
import os
from fastapi import FastAPI, HTTPException, WebSocket
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
    
@app.websocket("/ws/{symbol}")
async def stream_data(websocket: WebSocket, symbol: str):
    if symbol.lower() not in symbols:
        raise HTTPException(status_code=404, detail="Symbol not found")

    await websocket.accept()

    df = pd.read_csv(f"./Stocks/{symbol.lower()}.us.txt")
    df["Date"] = pd.to_datetime(df["Date"])

    for index in range(len(df)):
        row = df.iloc[index]
        await websocket.send_json({
            "Date": row["Date"].to_pydatetime().isoformat(),
            "Open": float(row["Open"]),
            "High": float(row["High"]),
            "Low": float(row["Low"]),
            "Close": float(row["Close"]),
            "Volume": int(row["Volume"]),
            "OpenInt": int(row["OpenInt"]) 
        })

        await asyncio.sleep(0.5)

    await websocket.close()