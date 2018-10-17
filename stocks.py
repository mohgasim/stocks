import numpy as np
import pandas as pd
from datetime import datetime
from time import sleep
from pandas_datareader import data as wb
from alpha_vantage.timeseries import TimeSeries

class StockIEX():

	def __init__(self, ticker, start, end = datetime.today().strftime('%Y-%m-%d')):
		self.ticker  = ticker.upper()
		self.start   = start
		self.end 	 = end
		print(f'\nCollecting {self.ticker} data from IEX.....')
		self.data  	 = wb.DataReader(self.ticker, data_source = 'iex', start = self.start, end = self.end)
		print(f'Data collection complete.')
		print(f'Organizing data.....')
		self.open    = self.data['open']
		self.high	 = self.data['high']
		self.low 	 = self.data['low']
		self.close   = self.data['close']
		self.volume  = self.data['volume']
		self.annual_return 	   = (self.close/self.close.shift(1) - 1).mean()*250
		self.return_volatility = ((self.close/self.close.shift(1) - 1).std())*(250**0.5)
		self.return_per_unit_vol = self.annual_return/self.return_volatility
		print(f'Data organization complete.')

	def summary(self):
		print(self.ticker)
		print(f'Stats Based On Unadjusted Closing Price, from {self.start} to {self.end}')
		print('Annual Return    : {0:.2f}%'.format(round(self.annual_return, 4)*100))
		print('Return Volatility: {0:.2f}%'.format(round(self.return_volatility, 4)*100))
		print('Return/Volatility: {0:.2f}'.format(round(self.return_per_unit_vol, 4)))

class TickerListIEX():

	def __init__(self, tickers, start, end = datetime.today().strftime('%Y-%m-%d')):
		self.tickers = tickers
		self.start = start
		self.end = end
		self.dict = {}
		for ticker in self.tickers:
			self.dict[ticker] = StockIEX(ticker.upper(), self.start, self.end)
		global data 
		data = self.dict

	def gen_summary(self):
		
		an_ret = []
		ret_vol = []
		ret_per_vol = []
		for ticker in self.tickers:
			an_ret.append(data[ticker].annual_return)
			ret_vol.append(data[ticker].return_volatility)
			ret_per_vol.append(data[ticker].return_per_unit_vol)

		global summary	
		summary = pd.DataFrame()
		summary['ticker'] = self.tickers
		summary['annual_return'] = an_ret
		summary['return_volatility'] = ret_vol
		summary['return_per_unit_vol'] = ret_per_vol
		summary = summary.sort_values('return_per_unit_vol', ascending = False).reset_index(drop = True)
		return summary


class StockAV():

	def __init__(self, ticker, start = None, end = datetime.today().strftime('%Y-%m-%d'), key = None):

		self.key = key
		if self.key == None:
			print("You must obtain a key to use Alpha Vantage.")
			print('Visit https://www.alphavantage.co/ to claim a free key.')
			print('Then insert your key as a string attribute.')
		else:
			self.ticker = ticker.upper()
			self.start = start
			self.end = end
			print(f'\nCollecting {self.ticker} data from Aplha Vantage.....')
			ts = TimeSeries(key = self.key, output_format = 'pandas')
			x, meta = ts.get_daily_adjusted(self.ticker, outputsize = 'full')
			print(f'Data collection complete.')
			print(f'Organizing data.....')
			x.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume', 'dividend_amount', 'split_coef']
			self.data 		= x[self.start:self.end]
			self.open 		= self.data.open
			self.high 		= self.data.high
			self.low 		= self.data.low
			self.close 		= self.data.close
			self.adj_close 	= self.data.adj_close
			self.holding_period = len(self.data)
			self.holding_return = (self.adj_close[-1] / self.adj_close[0]) - 1
			self.volume 	= self.data.volume
			self.dividends 	= self.data.dividend_amount
			self.split_coef = self.data.split_coef
			self.meta		= meta
			self.annual_return = ((self.adj_close/self.adj_close.shift(1)) - 1).mean()*250
			self.return_volatility = (((self.adj_close/self.adj_close.shift(1)) - 1).std())*(250**0.5)
			self.return_per_unit_vol = self.annual_return/self.return_volatility
			self.adjustments = self.data[(self.data['dividend_amount'] != 0) | (self.data['split_coef'] != 1)]

			if self.start == None:
				self.start = self.data.index[0]

			print(f'Data organization complete.')

	def summary(self):
		print(self.ticker)
		print(f'Stats Based On Adjusted Closing Price, from {self.start} to {self.end}')
		print(f'Holding Period	 : {self.holding_period} trading days')
		print('Holding Return	 : {0:.2f}%'.format(round(self.holding_return, 4)*100))
		print('Annual Return    : {0:.2f}%'.format(round(self.annual_return, 4)*100))
		print('Return Volatility: {0:.2f}%'.format(round(self.return_volatility, 4)*100))
		print('Return/Volatility: {0:.2f}'.format(round(self.return_per_unit_vol, 4)))

	def by_year(self):

		data = pd.DataFrame()
		data['adj_close'] = self.adj_close
		data['year'] = self.adj_close.index
		data['year'] = data.year.apply(lambda x: x.split('-')[0])

		years = data.year.unique()
		year_values = {}

		for y in years:
			temp = []
			for i in range(len(data)):
				if data.year[i] == y:
					temp.append(data.adj_close[i])
			year_values[y] = temp

		returns_by_year = pd.DataFrame()

		returns_by_year['year'] = years
		returns = []

		for year in years:

			x = year_values[str(year)][-1]
			y = year_values[str(year)][0]
			z = (x/y) - 1
			returns.append(z)

		returns_by_year['holding_return'] = returns

		return returns_by_year

class TickerListAV():

	def __init__(self, tickers, start = None, end = datetime.today().strftime('%Y-%m-%d')):
		self.tickers = tickers
		self.start = start
		self.end = end
		self.dict = {}

		if len(self.tickers) > 5:
			print('\nAlpha Vantange limits API calls to 5 per minute.')
			print(f'This will take approximately {((len(self.tickers*10)//60)+1)} minutes.')
			print('Please wait.....')
			for ticker in self.tickers:
				self.dict[ticker] = StockAV(ticker.upper(), self.start, self.end)
				sleep(10)
		else:
			for ticker in self.tickers:
				self.dict[ticker] = StockAV(ticker.upper(), self.start, self.end)

		global data 
		data = self.dict

	def gen_summary(self):
		
		an_ret = []
		ret_vol = []
		ret_per_vol = []
		for ticker in self.tickers:
			an_ret.append(data[ticker].annual_return)
			ret_vol.append(data[ticker].return_volatility)
			ret_per_vol.append(data[ticker].return_per_unit_vol)

		global summary	
		summary = pd.DataFrame()
		summary['ticker'] = self.tickers
		summary['annual_return'] = an_ret
		summary['return_volatility'] = ret_vol
		summary['return_per_unit_vol'] = ret_per_vol
		summary = summary.sort_values('return_per_unit_vol', ascending = False).reset_index(drop = True)
		return summary


if __name__ == '__main__':
	print('This is a module and should be imported into another script.')
	print('By Mohammed Gasim.')
	x = StockAV('tsla', key = 'XUPW4RL3WF2RVXFY')
	print(x.by_year())
