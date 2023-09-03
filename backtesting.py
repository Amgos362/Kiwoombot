import pandas as pd
import pymysql

conn = pymysql.connect(host='127.0.0.1', user='root', password='Quantum45**', db='INVESTAR', charset='utf8')
sql = "SELECT code, date, open, high, low, close, volume FROM daily_price"
original_df = pd.read_sql(sql, conn)
codes = pd.read_excel('real_codes.xlsx')
codes['code'] = codes['code'].apply(lambda x: str(x).zfill(6))

start_value = 1000000  # 시작 포트폴리오 가치
successful_trades = 0  # 양수 수익률을 보이는 경우의 수
testcase = len(codes)
k = 1000

successful_records = []

for idx, code_row in codes.iterrows():
    if idx >= testcase:
        break

    code = code_row['code']
    current_df = original_df[(original_df['code'] == code) & (original_df['volume'] != 0)].copy()
    current_df = current_df.tail(k)
    current_df = current_df.dropna()
    current_df = current_df.reset_index(drop=True)

    # 지표 계산
    current_df['original'] = (((current_df['high'] - current_df['low'])/current_df['volume'])/current_df['close']).rolling(window=10).mean()
    low = current_df['original'].rolling(window=20).min()
    high = current_df['original'].rolling(window=20).max()
    current_df['indicator'] = ((high - current_df['original']) / (high - low)) * 100
    current_df['indicator'] = current_df['indicator'].rolling(window=10).mean()


    portfolio = {'cash': 1000000, 'stock': 0}  # 1백만원 현금으로 시작

    # 매수/매도 신호 초기화
    current_df['signal'] = 0

    # 매수 신호 설정
    current_df.loc[current_df['indicator'] <= 10, 'signal'] = 1

    # 매도 신호 설정
    current_df.loc[current_df['indicator'] >= 90, 'signal'] = -1

    # 포트폴리오 성과 추적
    # 포트폴리오 성과 추적
    for idx, row in current_df.iterrows():

        if row['signal'] == 1:  # 매수 신호
            # 전체 현금으로 매수하고, 수수료 0.015% 고려
            portfolio['stock'] += portfolio['cash'] / row['close'] * 0.99985
            portfolio['cash'] = 0

        elif row['signal'] == -1:  # 매도 신호
            # 전체 주식을 매도하고, 수수료 0.015% 고려
            portfolio['cash'] += portfolio['stock'] * row['close'] * 0.99785
            portfolio['stock'] = 0

        # 포트폴리오 총 가치 계산 (주식 가치 + 현금)
        current_df.loc[idx, 'portfolio_value'] = portfolio['stock'] * row['close'] + portfolio['cash']

    final_value = portfolio['cash']
    if portfolio['stock'] != 0:
        final_value += portfolio['stock'] * current_df['close'].iloc[-1]

    profit_rate = ((final_value - start_value) / start_value) * 100
    if profit_rate > 0:
        successful_trades += 1
        successful_records.append({'code': code, 'profit_rate': profit_rate})

    print(f"Code: {code}, Portfolio: {portfolio}, Final Value: {final_value:.2f}, Profit Rate: {profit_rate:.2f}%")

success_rate = (successful_trades / testcase) * 100  # 5회의 거래 중 성공한 거래의 비율
print(f"Success Rate: {success_rate:.2f}%")

successful_df = pd.DataFrame(successful_records)
successful_df.to_excel('successful.xlsx', index=False)

