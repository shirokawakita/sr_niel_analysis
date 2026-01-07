"""
SR-NIEL PDF解析と可視化ツール

SR-NIELのPDF結果ファイルからprotonとelectronのNIELデータを抽出し、
CSV形式で保存、さらにグラフをPNG形式で出力します。
"""

import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import os
import argparse
from pathlib import Path


def extract_table_from_pdf(pdf_path):
    """
    PDFファイルから表データを抽出する
    
    Parameters:
    -----------
    pdf_path : str
        PDFファイルのパス
    
    Returns:
    --------
    list
        抽出された表データのリスト
    """
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # ページから表を抽出
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception as e:
        print(f"PDFの読み込みエラー ({pdf_path}): {e}")
        return None
    
    return tables


def clean_and_parse_data(tables):
    """
    抽出した表データをクリーニングし、エネルギーとNIEL値を抽出
    
    Parameters:
    -----------
    tables : list
        抽出された表データのリスト
    
    Returns:
    --------
    pandas.DataFrame
        クリーニングされたデータ（Energy, NIEL列）
    """
    data_rows = []
    
    # 最初の表でヘッダーを見つけて、列インデックスを決定
    energy_col_idx = None
    niel_col_idx = None
    
    # 最初の表でヘッダーを探す
    for table in tables:
        if not table:
            continue
        
        for row in table:
            if not row:
                continue
            
            # ヘッダー行を探す
            for col_idx, cell in enumerate(row):
                if cell:
                    cell_lower = str(cell).lower().replace('\n', ' ').replace(' ', '')
                    # エネルギー列を探す
                    if 'energy' in cell_lower or ('mev' in cell_lower and 'niel' not in cell_lower):
                        if energy_col_idx is None:
                            energy_col_idx = col_idx
                    # NIEL列を探す（NIEL Doseではない列）
                    if 'niel' in cell_lower and 'dose' not in cell_lower and 'mevcm' in cell_lower.replace(' ', ''):
                        if niel_col_idx is None:
                            niel_col_idx = col_idx
            
            # 両方の列が見つかったら終了
            if energy_col_idx is not None and niel_col_idx is not None:
                break
        
        # ヘッダーが見つかったら終了
        if energy_col_idx is not None and niel_col_idx is not None:
            break
    
    # 列インデックスが見つからない場合、デフォルト値を使用（通常は0と1）
    if energy_col_idx is None:
        energy_col_idx = 0
    if niel_col_idx is None:
        niel_col_idx = 1
    
    print(f"エネルギー列インデックス: {energy_col_idx}, NIEL列インデックス: {niel_col_idx}")
    
    # すべての表からデータを抽出
    for table_idx, table in enumerate(tables):
        if not table:
            continue
        
        header_skipped = False
        
        for row_idx, row in enumerate(table):
            if not row or len(row) <= max(energy_col_idx, niel_col_idx):
                continue
            
            # 最初の行がヘッダーの可能性があるので、数値パターンでチェック
            energy_str = str(row[energy_col_idx]).strip() if energy_col_idx < len(row) and row[energy_col_idx] else None
            niel_str = str(row[niel_col_idx]).strip() if niel_col_idx < len(row) and row[niel_col_idx] else None
            
            if not energy_str or not niel_str:
                continue
            
            # 数値パターンでデータ行かどうかを判定
            energy_match = re.search(r'[\d.]+(?:[eE][+-]?\d+)?', energy_str)
            niel_match = re.search(r'[\d.]+(?:[eE][+-]?\d+)?', niel_str)
            
            if energy_match and niel_match:
                try:
                    energy = float(energy_match.group())
                    niel = float(niel_match.group())
                    
                    # 有効な値のみを追加（エネルギーが0より大きく、NIELが0以上）
                    if energy > 0 and niel >= 0:
                        data_rows.append({'Energy (MeV)': energy, 'NIEL (MeV cm^2 g^-1)': niel})
                except (ValueError, IndexError) as e:
                    continue
    
    if not data_rows:
        return None
    
    df = pd.DataFrame(data_rows)
    # 重複を除去し、エネルギーでソート
    df = df.drop_duplicates(subset=['Energy (MeV)']).sort_values('Energy (MeV)').reset_index(drop=True)
    
    return df


def extract_niel_data_from_pdf(pdf_path):
    """
    PDFファイルからNIELデータを抽出する（メイン関数）
    
    Parameters:
    -----------
    pdf_path : str
        PDFファイルのパス
    
    Returns:
    --------
    pandas.DataFrame
        抽出されたNIELデータ
    """
    print(f"PDFファイルを読み込み中: {pdf_path}")
    tables = extract_table_from_pdf(pdf_path)
    
    if not tables:
        print(f"警告: {pdf_path}から表を抽出できませんでした")
        return None
    
    print(f"抽出された表の数: {len(tables)}")
    df = clean_and_parse_data(tables)
    
    if df is None or df.empty:
        print(f"警告: {pdf_path}から有効なデータを抽出できませんでした")
        return None
    
    print(f"抽出されたデータポイント数: {len(df)}")
    return df


def save_to_csv(df, output_path):
    """
    データフレームをCSV形式で保存
    
    Parameters:
    -----------
    df : pandas.DataFrame
        保存するデータフレーム
    output_path : str
        出力ファイルのパス
    """
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"CSVファイルを保存しました: {output_path}")


def calculate_ddd(niel_df, fluence):
    """
    NIELデータからDDD（Displacement Damage Dose）を計算
    
    Parameters:
    -----------
    niel_df : pandas.DataFrame
        NIELデータ（Energy, NIEL列を含む）
    fluence : float
        フルエンス（cm^-2）
    
    Returns:
    --------
    pandas.DataFrame
        DDDデータ（Energy, DDD列を含む）
    """
    df = niel_df.copy()
    # DDD = NIEL × フルエンス
    # NIELの単位: MeV cm²/g
    # フルエンスの単位: cm⁻²
    # DDDの単位: (MeV cm²/g) × (cm⁻²) = MeV/g
    df['DDD (MeV/g)'] = df['NIEL (MeV cm^2 g^-1)'] * fluence
    return df


def calculate_defect_density(ddd_df, density=2.33, eta=0.8, Ed=25.0):
    """
    DDDから欠陥数密度を計算（NRTモデル）
    
    Parameters:
    -----------
    ddd_df : pandas.DataFrame
        DDDデータ（Energy, DDD列を含む）
    density : float
        材料の密度（g/cm³）、デフォルトはシリコンの2.33 g/cm³
    eta : float
        欠陥生成効率（NRTモデル）、デフォルトは0.8
    Ed : float
        はじき出ししきい値（eV）、デフォルトはシリコンの25 eV
    
    Returns:
    --------
    pandas.DataFrame
        欠陥数密度データ（Energy, Defect Density列を含む）
    """
    df = ddd_df.copy()
    
    # 単位換算定数
    # EdをeVからMeVに変換: Ed[eV] × 1.602×10⁻¹⁹ = Ed[J]
    # 1 MeV = 1.602×10⁻¹³ J
    # したがって、Ed[MeV] = Ed[eV] × 10⁻⁶
    Ed_MeV = Ed * 1e-6  # eVからMeVへ変換
    
    # 欠陥数密度の計算式（NRTモデル）
    # 欠陥数密度 (cm⁻³) = (DDD × ρ × η) / (2 × Ed)
    # DDD: MeV/g
    # ρ: g/cm³
    # η: 無次元
    # Ed: MeV
    # 単位確認: (MeV/g) × (g/cm³) × (無次元) / (MeV) = cm⁻³
    
    df['Defect Density (cm^-3)'] = (df['DDD (MeV/g)'] * density * eta) / (2.0 * Ed_MeV)
    
    return df


def create_plot(proton_df, electron_df, output_path):
    """
    protonとelectronのNIELデータをプロットしてPNG形式で保存
    
    Parameters:
    -----------
    proton_df : pandas.DataFrame
        protonのNIELデータ
    electron_df : pandas.DataFrame
        electronのNIELデータ
    output_path : str
        出力ファイルのパス
    """
    plt.figure(figsize=(10, 6))
    
    # protonデータをプロット（red）
    if proton_df is not None and not proton_df.empty:
        plt.plot(proton_df['Energy (MeV)'], 
                proton_df['NIEL (MeV cm^2 g^-1)'],
                'o-', color='red', label='Proton', markersize=4, linewidth=1.5)
    
    # electronデータをプロット（blue）
    if electron_df is not None and not electron_df.empty:
        plt.plot(electron_df['Energy (MeV)'], 
                electron_df['NIEL (MeV cm^2 g^-1)'],
                's-', color='blue', label='Electron', markersize=4, linewidth=1.5)
    
    plt.xlabel('Energy (MeV)', fontsize=12)
    plt.ylabel('NIEL (MeV cm² g⁻¹)', fontsize=12)
    plt.title('SR-NIEL: Non-Ionizing Energy Loss for Silicon', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    
    # 対数スケールを設定
    plt.xscale('log')
    plt.yscale('log')
    
    # axオブジェクトを取得して補助線を詳細に設定
    ax = plt.gca()
    
    # メイン補助線（major grid）をdotスタイルで表示
    ax.grid(True, which='major', alpha=0.4, linestyle=':', linewidth=0.8, color='gray')
    
    # サブ補助線（minor grid）をより細いdotスタイルで表示
    ax.grid(True, which='minor', alpha=0.2, linestyle=':', linewidth=0.5, color='gray')
    
    # minor ticksを有効化
    ax.minorticks_on()
    
    # レイアウトを調整
    plt.tight_layout()
    
    # PNG形式で保存（高解像度）
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"グラフを保存しました: {output_path}")
    plt.close()


def calculate_defect_generation_rate(defect_df, fluence):
    """
    欠陥数密度から欠陥生成率を計算
    
    Parameters:
    -----------
    defect_df : pandas.DataFrame
        欠陥数密度データ（Energy, Defect Density列を含む）
    fluence : float
        フルエンス（cm^-2）
    
    Returns:
    --------
    pandas.DataFrame
        欠陥生成率データ（Energy, Defect Generation Rate列を含む）
    """
    df = defect_df.copy()
    # 欠陥生成率 = 欠陥密度 / フルエンス
    # 単位: (cm^-3) / (cm^-2) = cm^-1
    df['Defect Generation Rate (cm^-1)'] = df['Defect Density (cm^-3)'] / fluence
    return df


def create_defect_density_plot(proton_defect_df, electron_defect_df, output_path, fluence):
    """
    protonとelectronの欠陥数密度データをプロットしてPNG形式で保存
    
    Parameters:
    -----------
    proton_defect_df : pandas.DataFrame
        protonの欠陥数密度データ（Energy, Defect Density列を含む）
    electron_defect_df : pandas.DataFrame
        electronの欠陥数密度データ（Energy, Defect Density列を含む）
    output_path : str
        出力ファイルのパス
    fluence : float
        使用したフルエンス（表示用）
    """
    plt.figure(figsize=(10, 6))
    
    # protonデータをプロット（red）
    if proton_defect_df is not None and not proton_defect_df.empty:
        plt.plot(proton_defect_df['Energy (MeV)'], 
                proton_defect_df['Defect Density (cm^-3)'],
                'o-', color='red', label='Proton', markersize=4, linewidth=1.5)
    
    # electronデータをプロット（blue）
    if electron_defect_df is not None and not electron_defect_df.empty:
        plt.plot(electron_defect_df['Energy (MeV)'], 
                electron_defect_df['Defect Density (cm^-3)'],
                's-', color='blue', label='Electron', markersize=4, linewidth=1.5)
    
    plt.xlabel('Energy (MeV)', fontsize=12)
    plt.ylabel('Defect Density (cm^-3)', fontsize=12)
    plt.title(f'Defect Density vs Energy (Fluence: {fluence:.2e} cm^-2)', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    
    # 対数スケールを設定
    plt.xscale('log')
    plt.yscale('log')
    
    # axオブジェクトを取得して補助線を詳細に設定
    ax = plt.gca()
    
    # メイン補助線（major grid）をdotスタイルで表示
    ax.grid(True, which='major', alpha=0.4, linestyle=':', linewidth=0.8, color='gray')
    
    # サブ補助線（minor grid）をより細いdotスタイルで表示
    ax.grid(True, which='minor', alpha=0.2, linestyle=':', linewidth=0.5, color='gray')
    
    # minor ticksを有効化
    ax.minorticks_on()
    
    # レイアウトを調整
    plt.tight_layout()
    
    # PNG形式で保存（高解像度）
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"グラフを保存しました: {output_path}")
    plt.close()


def create_defect_generation_rate_plot(proton_rate_df, electron_rate_df, output_path):
    """
    protonとelectronの欠陥生成率データをプロットしてPNG形式で保存
    
    Parameters:
    -----------
    proton_rate_df : pandas.DataFrame
        protonの欠陥生成率データ（Energy, Defect Generation Rate列を含む）
    electron_rate_df : pandas.DataFrame
        electronの欠陥生成率データ（Energy, Defect Generation Rate列を含む）
    output_path : str
        出力ファイルのパス
    """
    plt.figure(figsize=(10, 6))
    
    # protonデータをプロット（red）
    if proton_rate_df is not None and not proton_rate_df.empty:
        plt.plot(proton_rate_df['Energy (MeV)'], 
                proton_rate_df['Defect Generation Rate (cm^-1)'],
                'o-', color='red', label='Proton', markersize=4, linewidth=1.5)
    
    # electronデータをプロット（blue）
    if electron_rate_df is not None and not electron_rate_df.empty:
        plt.plot(electron_rate_df['Energy (MeV)'], 
                electron_rate_df['Defect Generation Rate (cm^-1)'],
                's-', color='blue', label='Electron', markersize=4, linewidth=1.5)
    
    plt.xlabel('Energy (MeV)', fontsize=12)
    plt.ylabel('Defect Generation Rate (cm^-1)', fontsize=12)
    plt.title('Defect Generation Rate vs Energy', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    
    # 対数スケールを設定
    plt.xscale('log')
    plt.yscale('log')
    
    # axオブジェクトを取得して補助線を詳細に設定
    ax = plt.gca()
    
    # メイン補助線（major grid）をdotスタイルで表示
    ax.grid(True, which='major', alpha=0.4, linestyle=':', linewidth=0.8, color='gray')
    
    # サブ補助線（minor grid）をより細いdotスタイルで表示
    ax.grid(True, which='minor', alpha=0.2, linestyle=':', linewidth=0.5, color='gray')
    
    # minor ticksを有効化
    ax.minorticks_on()
    
    # レイアウトを調整
    plt.tight_layout()
    
    # PNG形式で保存（高解像度）
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"グラフを保存しました: {output_path}")
    plt.close()


def main():
    """
    メイン処理
    """
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(
        description='SR-NIEL PDF解析と可視化ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python extract_niel_data.py proton.pdf electron.pdf
  python extract_niel_data.py "SR-NIEL Results_silicon_proton.pdf" "SR-NIEL Results_silicon_electron.pdf"
        """
    )
    parser.add_argument('proton_pdf', type=str, 
                       help='ProtonのNIELデータが含まれるPDFファイルのパス')
    parser.add_argument('electron_pdf', type=str,
                       help='ElectronのNIELデータが含まれるPDFファイルのパス')
    
    args = parser.parse_args()
    
    # ファイルパスの設定
    proton_pdf = Path(args.proton_pdf)
    electron_pdf = Path(args.electron_pdf)
    
    # 相対パスの場合は現在のディレクトリを基準にする
    if not proton_pdf.is_absolute():
        proton_pdf = Path.cwd() / proton_pdf
    
    if not electron_pdf.is_absolute():
        electron_pdf = Path.cwd() / electron_pdf
    
    # PDFファイルの存在確認
    if not proton_pdf.exists():
        print(f"エラー: {proton_pdf}が見つかりません")
        return
    
    if not electron_pdf.exists():
        print(f"エラー: {electron_pdf}が見つかりません")
        return
    
    # 出力ディレクトリは最初のPDFファイルと同じディレクトリ
    base_dir = proton_pdf.parent
    
    # Protonデータの抽出
    print("\n=== Protonデータの抽出 ===")
    proton_df = extract_niel_data_from_pdf(str(proton_pdf))
    
    # Electronデータの抽出
    print("\n=== Electronデータの抽出 ===")
    electron_df = extract_niel_data_from_pdf(str(electron_pdf))
    
    # データの保存
    if proton_df is not None and not proton_df.empty:
        proton_csv = base_dir / "niel_proton.csv"
        save_to_csv(proton_df, str(proton_csv))
        print(f"Protonデータの統計:\n{proton_df.describe()}\n")
    else:
        print("警告: Protonデータが抽出できませんでした")
    
    if electron_df is not None and not electron_df.empty:
        electron_csv = base_dir / "niel_electron.csv"
        save_to_csv(electron_df, str(electron_csv))
        print(f"Electronデータの統計:\n{electron_df.describe()}\n")
    else:
        print("警告: Electronデータが抽出できませんでした")
    
    # グラフの作成
    if (proton_df is not None and not proton_df.empty) or \
       (electron_df is not None and not electron_df.empty):
        plot_path = base_dir / "niel_plot.png"
        create_plot(proton_df, electron_df, str(plot_path))
        print("\n処理が完了しました！")
    else:
        print("\nエラー: グラフを作成するためのデータがありません")
    
    # 欠陥数密度の計算
    print("\n=== 欠陥数密度の計算 ===")
    fluence = 1e14  # cm^-2
    
    # パラメータ設定（シリコン用）
    density = 2.33  # g/cm³
    eta = 0.8  # NRTモデルの欠陥生成効率
    Ed = 25.0  # eV（はじき出ししきい値）
    
    print(f"フルエンス: {fluence:.2e} cm^-2")
    print(f"密度: {density} g/cm^3")
    print(f"欠陥生成効率（eta）: {eta}")
    print(f"はじき出ししきい値（Ed）: {Ed} eV")
    
    # Protonの欠陥数密度計算
    proton_defect_df = None
    if proton_df is not None and not proton_df.empty:
        print("\n--- Protonの欠陥数密度計算 ---")
        proton_ddd_df = calculate_ddd(proton_df, fluence)
        proton_defect_df = calculate_defect_density(proton_ddd_df, density, eta, Ed)
        
        # 欠陥数密度データの保存
        defect_proton_csv = base_dir / "defect_density_proton.csv"
        save_df = proton_defect_df[['Energy (MeV)', 'Defect Density (cm^-3)']].copy()
        save_to_csv(save_df, str(defect_proton_csv))
        print(f"Proton欠陥数密度の統計:\n{proton_defect_df['Defect Density (cm^-3)'].describe()}\n")
    
    # Electronの欠陥数密度計算
    electron_defect_df = None
    if electron_df is not None and not electron_df.empty:
        print("\n--- Electronの欠陥数密度計算 ---")
        electron_ddd_df = calculate_ddd(electron_df, fluence)
        electron_defect_df = calculate_defect_density(electron_ddd_df, density, eta, Ed)
        
        # 欠陥数密度データの保存
        defect_electron_csv = base_dir / "defect_density_electron.csv"
        save_df = electron_defect_df[['Energy (MeV)', 'Defect Density (cm^-3)']].copy()
        save_to_csv(save_df, str(defect_electron_csv))
        print(f"Electron欠陥数密度の統計:\n{electron_defect_df['Defect Density (cm^-3)'].describe()}\n")
    
    # 欠陥数密度のグラフ作成
    if (proton_defect_df is not None and not proton_defect_df.empty) or \
       (electron_defect_df is not None and not electron_defect_df.empty):
        defect_plot_path = base_dir / "defect_density_plot.png"
        create_defect_density_plot(proton_defect_df, electron_defect_df, 
                                   str(defect_plot_path), fluence)
        print("\n欠陥数密度の計算とグラフ出力が完了しました！")
    else:
        print("\n警告: 欠陥数密度のグラフを作成するためのデータがありません")
    
    # 欠陥生成率の計算
    print("\n=== 欠陥生成率の計算 ===")
    
    # Protonの欠陥生成率計算
    proton_rate_df = None
    if proton_defect_df is not None and not proton_defect_df.empty:
        print("\n--- Protonの欠陥生成率計算 ---")
        proton_rate_df = calculate_defect_generation_rate(proton_defect_df, fluence)
        
        # 欠陥生成率データの保存
        rate_proton_csv = base_dir / "defect_generation_rate_proton.csv"
        save_df = proton_rate_df[['Energy (MeV)', 'Defect Generation Rate (cm^-1)']].copy()
        save_to_csv(save_df, str(rate_proton_csv))
        print(f"Proton欠陥生成率の統計:\n{proton_rate_df['Defect Generation Rate (cm^-1)'].describe()}\n")
    
    # Electronの欠陥生成率計算
    electron_rate_df = None
    if electron_defect_df is not None and not electron_defect_df.empty:
        print("\n--- Electronの欠陥生成率計算 ---")
        electron_rate_df = calculate_defect_generation_rate(electron_defect_df, fluence)
        
        # 欠陥生成率データの保存
        rate_electron_csv = base_dir / "defect_generation_rate_electron.csv"
        save_df = electron_rate_df[['Energy (MeV)', 'Defect Generation Rate (cm^-1)']].copy()
        save_to_csv(save_df, str(rate_electron_csv))
        print(f"Electron欠陥生成率の統計:\n{electron_rate_df['Defect Generation Rate (cm^-1)'].describe()}\n")
    
    # 欠陥生成率のグラフ作成
    if (proton_rate_df is not None and not proton_rate_df.empty) or \
       (electron_rate_df is not None and not electron_rate_df.empty):
        rate_plot_path = base_dir / "defect_generation_rate_plot.png"
        create_defect_generation_rate_plot(proton_rate_df, electron_rate_df, str(rate_plot_path))
        print("\n欠陥生成率の計算とグラフ出力が完了しました！")
    else:
        print("\n警告: 欠陥生成率のグラフを作成するためのデータがありません")


if __name__ == "__main__":
    main()

