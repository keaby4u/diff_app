import pandas as pd

# file_path_or_buffer = "D:/杂活/wff_配方比较/PS1419 (1).xlsx"  # 替换为实际的文件路径或文件对象
def read_recipe_excel(file_path_or_buffer) -> pd.DataFrame:
    """
    自动识别餐厅或供应链 Excel，提取标准字段和展示字段，避免字段重复。
    返回字段：fg_code, item_code, item_name, dosage, unit, product_name（如有） + 展示字段
    """

    df_raw = pd.read_excel(file_path_or_buffer, dtype=str)
    df_raw.columns = df_raw.columns.str.strip()

    if df_raw.columns.str.contains("Unnamed").all():
        df_raw = pd.read_excel(file_path_or_buffer, dtype=str, header=1)
        df_raw.columns = df_raw.columns.str.strip()

    is_restaurant = "FG CODE" in df_raw.columns and "配方用量" in df_raw.columns
    is_supplier = "SP Product Code" in df_raw.columns and "Quantity" in df_raw.columns

    if not is_restaurant and not is_supplier:
        raise ValueError("无法识别 Excel 表结构，字段缺失。")

    if is_restaurant:
        col_map = {
            "FG CODE": "fg_code",
            "货品编码集合": "item_code",
            "货品名称集合": "item_name",
            "配方用量": "dosage",
            "配方编码单位": "unit",
            "产品名称": "product_name",
        }

        extra_fields = {
            "产品编码": "餐厅_产品编码",
            "产品名称": "餐厅_产品名称",
            "销量": "餐厅_销量",
            "配方编码": "餐厅_配方编码",
            "配方名称": "餐厅_配方名称",
        }

    else:
        col_map = {
            "SP Product Code": "fg_code",
            "JDE Code": "item_code",
            "JDE Name": "item_name",
            "Quantity": "dosage",
            "Unit(BOM)": "unit"
        }

        extra_fields = {
            "SP Product Name": "供应链_SP Product Name",
        }

    col_map = {k: v for k, v in col_map.items() if k in df_raw.columns}

    # 避免展示字段重名
    extra_fields_clean = {}
    seen_names = set()
    for orig, new in extra_fields.items():
        if orig in df_raw.columns:
            suffix = 1
            final = new
            while final in seen_names:
                suffix += 1
                final = f"{new}_{suffix}"
            extra_fields_clean[orig] = final
            seen_names.add(final)

    extra_fields_clean = {}
    seen_names = set()
    for orig, new in extra_fields.items():
        if orig in df_raw.columns:
            # 如果原始表中该字段出现多次，取第一个
            matching_cols = [col for col in df_raw.columns if col.strip() == orig]
            if len(matching_cols) > 1:
                # 如果有多个“产品名称”，只取第一个
                first_occurrence = matching_cols[0]
            else:
                first_occurrence = orig

            # 确保目标列名唯一
            suffix = 1
            final_name = new
            while final_name in seen_names:
                suffix += 1
                final_name = f"{new}_{suffix}"
            extra_fields_clean[first_occurrence] = final_name
            seen_names.add(final_name)

    df = df_raw[list(col_map.keys()) + list(extra_fields.keys())].rename(columns={**col_map, **extra_fields})

    df = df.dropna(subset=["fg_code", "item_code", "dosage"])
    df["dosage"] = pd.to_numeric(df["dosage"], errors="coerce")
    df = df.dropna(subset=["dosage"])
    df = df.drop_duplicates(subset=["fg_code", "item_code"])
    df = df.loc[:, ~df.columns.duplicated()]
    
    return df

# df_restaurant = read_recipe_excel("D:/杂活/wff_配方比较/PS1419 (1).xlsx")
# df_supplier = read_recipe_excel("D:/杂活/wff_配方比较/SPBOM_EXPORT_ALL_20250505_1.xlsx")

def compare_recipe_details(df_restaurant: pd.DataFrame, df_supplier: pd.DataFrame, tolerance: float = 0.05) -> pd.DataFrame:
    """
    对比每个 FG_CODE 的 SKU 是否一致、用量是否一致、单位是否一致，并输出差异说明。
    """

    df_restaurant["来源"] = "餐厅"
    df_supplier["来源"] = "供应链"

    df_all = pd.merge(
        df_restaurant,
        df_supplier,
        how="outer",
        on=["fg_code", "item_code"],
        suffixes=("_餐厅", "_供应链"),
        indicator=True
    )

    def classify(row):
        if row["_merge"] == "left_only":
            return "仅餐厅有"
        elif row["_merge"] == "right_only":
            return "仅供应链有"
        else:
            diff_info = []
            if abs((row["dosage_餐厅"] or 0) - (row["dosage_供应链"] or 0)) > tolerance:
                diff_info.append("用量不同")
            if row.get("unit_餐厅") != row.get("unit_供应链"):
                diff_info.append("单位不同")
            return "一致" if not diff_info else "；".join(diff_info)

    df_all["差异类型说明"] = df_all.apply(classify, axis=1)

    df_all["SKU是否一致"] = df_all["_merge"].apply(lambda x: "是" if x == "both" else "否")
    df_all["用量是否一致"] = df_all.apply(
        lambda r: "是" if r["_merge"] == "both" and abs((r["dosage_餐厅"] or 0) - (r["dosage_供应链"] or 0)) <= tolerance else "否", axis=1
    )
    df_all["单位是否一致"] = df_all.apply(
        lambda r: "是" if r["_merge"] == "both" and r.get("unit_餐厅") == r.get("unit_供应链") else "否", axis=1
    )

    # 输出字段（展示字段 + 核心字段）
    # base_cols = [
    #     "fg_code", "item_code",
    #     "item_name_餐厅", "item_name_供应链",
    #     "dosage_餐厅", "unit_餐厅",
    #     "dosage_供应链", "unit_供应链",
    #     "SKU是否一致", "用量是否一致", "单位是否一致", "差异类型说明"
    # ]
    # extra_cols = [c for c in df_all.columns if c.startswith("餐厅_") or c.startswith("供应链_")]
    return df_all


# dfx=df_all[extra_cols + base_cols]