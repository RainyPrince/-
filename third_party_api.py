from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional

# 1. 初始化FastAPI应用
app = FastAPI(title="法律条文API服务", version="1.0")

# 2. 定义法律条文数据模型
class LegalArticle(BaseModel):
    id: int
    title: str  # 如《民法典》第1043条
    content: str  # 条文内容
    category: str  # 法律类别（民法/刑法/劳动法）

# 3. 模拟法律条文数据库（实际项目可替换为数据库查询）
mock_legal_articles: List[LegalArticle] = [
    LegalArticle(
        id=1,
        title="《中华人民共和国民法典》第1043条",
        content="家庭应当树立优良家风，弘扬家庭美德，重视家庭文明建设。夫妻应当互相忠实，互相尊重，互相关爱；家庭成员应当敬老爱幼，互相帮助，维护平等、和睦、文明的婚姻家庭关系。",
        category="民法"
    ),
    LegalArticle(
        id=2,
        title="《中华人民共和国刑法》第264条",
        content="盗窃公私财物，数额较大的，或者多次盗窃、入户盗窃、携带凶器盗窃、扒窃的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金；数额巨大或者有其他严重情节的，处三年以上十年以下有期徒刑，并处罚金；数额特别巨大或者有其他特别严重情节的，处十年以上有期徒刑或者无期徒刑，并处罚金或者没收财产。",
        category="刑法"
    ),
    LegalArticle(
        id=3,
        title="《中华人民共和国劳动法》第44条",
        content="有下列情形之一的，用人单位应当按照下列标准支付高于劳动者正常工作时间工资的工资报酬：（一）安排劳动者延长工作时间的，支付不低于工资的百分之一百五十的工资报酬；（二）休息日安排劳动者工作又不能安排补休的，支付不低于工资的百分之二百的工资报酬；（三）法定休假日安排劳动者工作的，支付不低于工资的百分之三百的工资报酬。",
        category="劳动法"
    )
]

# API接口：获取法律条文（返回Object类型，避免JSON兼容问题）
@app.get(
    "/legal_articles",
    response_model=dict,
    description="根据类别筛选法律条文"
)
def get_legal_articles(
    category: Optional[str] = Query(None, description="法律类别（如：民法/刑法/劳动法）")
):
    # 筛选符合条件的条文
    filtered_articles = [art for art in mock_legal_articles if art.category == category] if category else mock_legal_articles
    # 返回Object格式（status/data/count）
    return {
        "status": "success",
        "data": filtered_articles,
        "count": len(filtered_articles),
        "message": "数据获取成功"
    }

# 添加Uvicorn启动逻辑（避免命令行reload警告）
if __name__ == "__main__":
    import uvicorn
    # 启动服务：关闭reload（消除警告），指定端口8000
    uvicorn.run(
        app="__main__:app",  # 关键：用导入字符串格式指定应用（模块名:应用实例名）
        host="127.0.0.1",
        port=8000,
        reload=False  # 关闭reload，避免警告；若需自动重载，可改为True（需确保Python版本≥3.8）
    )