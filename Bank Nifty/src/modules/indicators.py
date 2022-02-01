
def tr(data):
    data["previous_close"] = data["Close"].shift(1)
    data["high-low"] = abs(data["High"] - data["Low"])
    data["high-pc"] = abs(data["High"] - data["previous_close"])
    data["low-pc"] = abs(data["Low"] - data["previous_close"])
    return data[["high-low", "high-pc", "low-pc"]].max(axis=1)


def atr(data, period):
    data["tr"] = tr(data)
    return data["tr"].rolling(period).mean()


def supertrend(df, period, atr_multiplier):
    hl2 = (df["High"] + df["Low"]) / 2
    df["atr"] = atr(df, period)
    df["upperband"] = hl2 + (atr_multiplier * df["atr"])
    df["lowerband"] = hl2 - (atr_multiplier * df["atr"])
    df["in_uptrend"] = True

    for current in range(1, len(df.index)):

        previous = current - 1

        if df["Close"][current] > df["upperband"][previous]:
            df["in_uptrend"][current] = True

        elif df["Close"][current] < df["lowerband"][previous]:
            df["in_uptrend"][current] = False

        else:
            df["in_uptrend"][current] = df["in_uptrend"][previous]

            if (
                df["in_uptrend"][current]
                and df["lowerband"][current] < df["lowerband"][previous]
            ):
                df["lowerband"][current] = df["lowerband"][previous]

            if (
                not df["in_uptrend"][current]
                and df["upperband"][current] > df["upperband"][previous]
            ):
                df["upperband"][current] = df["upperband"][previous]
    return df


def rsi(df, periods=2, ema=True):
    """
    Returns a pd.Series with the relative strength index.
    """

    close_delta = df["Close"].diff()

    # Make two series: one for lower closes and one for higher closes

    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)

    if ema == True:
        # Use exponential moving average
        ma_up = up.ewm(com=periods - 1, adjust=True,
                       min_periods=periods).mean()
        ma_down = down.ewm(com=periods - 1, adjust=True,
                           min_periods=periods).mean()

    else:
        # Use simple moving average
        ma_up = up.rolling(window=periods, adjust=False).mean()
        ma_down = down.rolling(window=periods, adjust=False).mean()

    rsi = ma_up / ma_down
    rsi = 100 - (100 / (1 + rsi))
    return rsi
