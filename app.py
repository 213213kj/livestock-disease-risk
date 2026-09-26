from pathlib import Path

import pandas as pd
import streamlit as st


# 页面设置
st.set_page_config(
    page_title="畜禽疾病风险分析",
    page_icon="🐄",
    layout="wide",
)

# 以 app.py 所在位置为基准查找数据，避免依赖电脑上的固定路径。
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "畜牧养殖疾病数据集.csv"
RISK_ORDER = ["健康", "疑似患病", "已患病"]


@st.cache_data
def load_data(file_path: str) -> pd.DataFrame:
    """读取数据；缓存结果，筛选页面时不必反复从硬盘读取。"""
    return pd.read_csv(file_path, encoding="utf-8-sig")


st.title("畜禽疾病风险分析平台")
st.caption("浏览养殖记录、疾病风险等级分布，以及养殖环境和防疫指标与风险标签的统计关系。")

if not DATA_PATH.exists():
    st.error("没有找到数据文件。请把“畜牧养殖疾病数据集.csv”和 app.py 放在同一个文件夹里。")
    st.stop()

try:
    df = load_data(str(DATA_PATH))
except Exception as exc:
    st.error(f"读取数据失败：{exc}")
    st.stop()

required_columns = ["畜禽种类", "疾病风险等级"]
missing_columns = [column for column in required_columns if column not in df.columns]
if missing_columns:
    st.error(f"数据文件缺少必要字段：{', '.join(missing_columns)}")
    st.stop()

# 侧边栏筛选器
st.sidebar.header("筛选数据")
species_options = sorted(df["畜禽种类"].dropna().astype(str).unique().tolist())
risk_options = [risk for risk in RISK_ORDER if risk in df["疾病风险等级"].dropna().unique()]
region_options = sorted(df["所在区域"].dropna().astype(str).unique().tolist()) if "所在区域" in df.columns else []

selected_species = st.sidebar.multiselect("畜禽种类", species_options, default=species_options)
selected_risks = st.sidebar.multiselect("疾病风险等级", risk_options, default=risk_options)
selected_regions = st.sidebar.multiselect("所在区域", region_options, default=region_options) if region_options else []

filtered = df.copy()
if selected_species:
    filtered = filtered[filtered["畜禽种类"].astype(str).isin(selected_species)]
if selected_risks:
    filtered = filtered[filtered["疾病风险等级"].astype(str).isin(selected_risks)]
if region_options and selected_regions:
    filtered = filtered[filtered["所在区域"].astype(str).isin(selected_regions)]

if filtered.empty:
    st.warning("当前筛选条件下没有记录，请在左侧重新选择筛选项。")
    st.stop()

page = st.sidebar.radio(
    "查看页面",
    ["数据总览", "风险等级分布", "指标关系探索", "数据记录预览"],
)

if page == "数据总览":
    st.subheader("数据总览")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("筛选后记录数", f"{len(filtered):,}")
    c2.metric("原始字段数", f"{df.shape[1]}")
    c3.metric("畜禽种类数", f"{filtered['畜禽种类'].nunique()}")
    c4.metric("风险类别数", f"{filtered['疾病风险等级'].nunique()}")

    counts = filtered["疾病风险等级"].value_counts().reindex(RISK_ORDER, fill_value=0)
    st.markdown("#### 疾病风险等级样本数")
    st.bar_chart(counts.rename("样本数"), use_container_width=True)

    st.markdown("#### 字段示例")
    st.dataframe(filtered.head(8), use_container_width=True)

elif page == "风险等级分布":
    st.subheader("不同畜禽种类的风险等级构成")
    composition = pd.crosstab(
        filtered["畜禽种类"],
        filtered["疾病风险等级"],
        normalize="index",
    ).reindex(columns=RISK_ORDER, fill_value=0) * 100
    composition = composition.round(2)
    st.bar_chart(composition, use_container_width=True)
    st.dataframe(composition.rename_axis("畜禽种类"), use_container_width=True)
    st.caption("每一行按物种分别计算百分比；图表展示的是数据中的统计构成，不表示物种导致疾病。")

elif page == "指标关系探索":
    st.subheader("养殖指标与疾病风险标签")
    available = [
        column for column in ["氨气浓度(ppm)", "通风时长(小时/天)", "抗体水平等级"]
        if column in filtered.columns
    ]

    if "氨气浓度(ppm)" in filtered.columns and "通风时长(小时/天)" in filtered.columns:
        st.markdown("#### 氨气浓度与通风时长散点图")
        scatter_data = filtered[
            ["氨气浓度(ppm)", "通风时长(小时/天)", "疾病风险等级"]
        ].dropna()
        if len(scatter_data) > 3000:
            scatter_data = scatter_data.sample(n=3000, random_state=42)
        st.scatter_chart(
            scatter_data,
            x="氨气浓度(ppm)",
            y="通风时长(小时/天)",
            color="疾病风险等级",
            use_container_width=True,
        )
        st.caption("为保证网页响应速度，记录较多时随机展示最多 3000 条。散点只用于观察统计关系，不代表因果关系。")

    if "抗体水平等级" in available:
        st.markdown("#### 不同抗体水平下的疾病风险构成")
        antibody_composition = pd.crosstab(
            filtered["抗体水平等级"],
            filtered["疾病风险等级"],
            normalize="index",
        ).reindex(columns=RISK_ORDER, fill_value=0) * 100
        st.bar_chart(antibody_composition.round(2), use_container_width=True)
        st.dataframe(antibody_composition.round(2), use_container_width=True)

    if not available:
        st.info("当前数据中没有可用于展示的环境或防疫字段。")

elif page == "数据记录预览":
    st.subheader("筛选后的记录")
    st.caption(f"当前共 {len(filtered):,} 条；页面预览最多显示前 500 条。")
    st.dataframe(filtered.head(500), use_container_width=True)
    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="下载当前筛选数据",
        data=csv_bytes,
        file_name="筛选后的畜禽疾病风险数据.csv",
        mime="text/csv",
    )

st.divider()
st.caption("说明：本平台展示的是现有数据中的描述性统计和风险标签构成，不替代兽医诊断，也不能单独证明未来发病预警能力。")
