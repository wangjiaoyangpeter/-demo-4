from pathlib import Path
# 项目根目录
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
CSV_PATH = DATA_DIR / "stock_history.csv"
# 创建数据目录
DATA_DIR.mkdir(exist_ok=True)
# 第三方数据源
FINANCE_SITES = {
 "sina": "https://finance.sina.com.cn/realstock/company/{}/nc.shtml"
}
# 请求头
DEFAULT_HEADERS = {
 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}