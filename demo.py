from ib_insync import Stock, Option, util
import pandas as pd
import datetime
from services import calendar_service, contracts_service, ibapi_service, prices_service


class Main:
    def __init__(self, underlying_symbol, exchange, currency, spread_around_spot):
        # Connect to IB Gateway or TWS
        self.ib = ibapi_service.connect_to_ib()
        self.underlying = Stock(underlying_symbol, exchange, currency)
        self.spread_around_spot = spread_around_spot

        self.run()

    def run(self):
        self.get_underlying_conId()
        self.get_historical_bid_ask()

    def get_underlying_conId(self):
        contract_details = contracts_service.get_contract_details(
            self.ib, self.underlying
        )
        self.underlying.conId = contract_details[0].contract.conId

    def get_historical_bid_ask(self):
        # Get the expiration date for the 0DTE option
        expiration_date = calendar_service.get_0dte_expiration_date()

        # Request market data for underlying
        latest_price = prices_service.get_latest_price(self.underlying, self.ib)
        # print(f"Latest price: {latest_price}")

        # Get option chains for symbol and filter for SMART exchange
        chains = contracts_service.get_option_chains(self.ib, self.underlying)
        chain = [chain for chain in chains if chain.exchange == "SMART"][0]

        # Check if the expiration date is in the chain
        if expiration_date not in chain.expirations:
            raise ValueError("Expiration date not found in chain.")

        # Filter strikes around the spot price
        # We only want to fetch data for strikes that are within a certain range around the spot price
        strikes_to_fetch = [
            strike
            for strike in chain.strikes
            if strike > latest_price - self.spread_around_spot
            and strike < latest_price + self.spread_around_spot
        ]

        # Get all strikes for this expiration and create option contracts
        for strike in strikes_to_fetch:
            for right in ["C", "P"]:  # Call and Put options
                contract = Option(
                    symbol=self.underlying.symbol,
                    lastTradeDateOrContractMonth=expiration_date,
                    strike=strike,
                    right=right,
                    exchange="SMART",
                )

                # Request historical bid/ask data
                bid_bars = prices_service.get_historical_bars(
                    self.ib,
                    contract,
                    whatToShow="BID",
                    endDateTime="",
                    durationStr="1 D",
                    barSizeSetting="1 min",
                    useRTH=False,
                    formatDate=1,
                )

                # Convert to a pandas DataFrame for easier manipulation
                df_bid = util.df(bid_bars)

                if not bid_bars:
                    continue

                df_bid["Type"] = "Bid"

                ask_bars = prices_service.get_historical_bars(
                    self.ib,
                    contract,
                    whatToShow="ASK",
                    endDateTime="",
                    durationStr="1 D",
                    barSizeSetting="1 min",
                    useRTH=False,
                    formatDate=1,
                )

                # Convert to a pandas DataFrame for easier manipulation
                df_ask = util.df(ask_bars)

                if not ask_bars:
                    continue

                df_ask["Type"] = "Ask"  # Add a column to distinguish ask data

                # Combine bid and ask DataFrames into one
                df_combined = pd.concat([df_bid, df_ask])

                # Generate a filename using the strike price and option type (Call/Put)
                filename = f"raw_data/{self.underlying.symbol}_strike_{strike}_{right}_bid_ask.csv"

                # Save the combined DataFrame to a CSV file
                df_combined.to_csv(filename, index=False)

                print(f"Saved bid and ask data for {strike} {right} to {filename}")


if __name__ == "__main__":
    Main("SPY", "SMART", "USD", 10)
