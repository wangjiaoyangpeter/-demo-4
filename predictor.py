import pandas as pd
import numpy as np
from typing import Tuple, Dict
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
class FinancialPredictor:
    """
    财务指标预测器
    """
    def __init__(self, model_type: str = "random_forest"):
        """初始化预测器"""
        if model_type == "random_forest":
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        else:
            self.model = LinearRegression()
        self.model_type = model_type
    def _create_features(self, series: pd.Series) -> pd.DataFrame:
        """创建时间序列特征"""
        df = pd.DataFrame({'value': series})
        df['day'] = range(len(df))
        # 添加滞后特征
        for i in range(1, 6):
            df[f'lag_{i}'] = df['value'].shift(i)
        df.dropna(inplace=True)
        return df
    def predict_pe(self,pe_series: pd.Series,forecast_days: int = 7) -> Tuple[pd.DataFrame, Dict]:
        """
        预测市盈率走势
        Args:
        pe_series: 历史PE序列
        forecast_days: 预测天数
        Returns:
        forecast_df: 预测结果
        metrics: 模型评估指标
        """
        if len(pe_series) < 10:
            raise ValueError("历史数据不足，无法预测")
        # 特征工程
        feature_df = self._create_features(pe_series)
        X = feature_df.drop(columns=['value'])
        y = feature_df['value']
        # 训练模型
        self.model.fit(X, y)
        # 预测
        last_row = X.iloc[-1].values.reshape(1, -1)
        predictions = []
        temp_input = last_row.copy()
        for _ in range(forecast_days):
            pred = self.model.predict(temp_input)[0]
            predictions.append(pred)
            # 更新滞后特征（简化处理）
            temp_input = np.roll(temp_input, -1)
            temp_input[0, -1] = pred
        # 生成结果
        last_date = pe_series.index[-1]
        forecast_index = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days)
        forecast_df = pd.DataFrame({'predicted_PE': predictions}, index=forecast_index)
        # 计算评估指标（简单用最后部分做评估）
        test_size = min(5, len(y) // 5)
        if test_size > 1:
            X_test = X.iloc[-test_size:]
            y_test = y.iloc[-test_size:]
            y_pred = self.model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
        else:
            mae, r2 = float('nan'), float('nan')
        metrics = {
        'MAE': mae,
        'R2': r2,
        'model_type': self.model_type
        }
        return forecast_df, metrics