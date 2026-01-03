# SR-NIEL PDF解析と可視化ツール

SR-NIELのPDF結果ファイルからprotonとelectronのNIEL（Non-Ionizing Energy Loss）データを抽出し、CSV形式で保存、さらにグラフをPNG形式で出力するツールです。さらに、NIELデータから欠陥数密度と欠陥生成率を計算し、可視化します。

## データソース

このツールで使用するNIELデータは、[SR-NIEL Web計算機](https://www.sr-niel.org/index.php/sr-niel-web-calculators)から取得したPDF結果ファイルを使用します。

SR-NIEL（Screened Relativistic treatment for NIEL）は、粒子の非電離エネルギー損失（NIEL）を計算するためのWebベースの計算機です。以下の計算機を使用してNIELデータを取得できます：

- **NIEL and dose calculator for electrons, protons and ions** - 単一粒子のNIEL計算
- **NIEL and dose calculator for spectral fluence of electrons, protons and ions** - スペクトルフルエンスのNIEL計算

### データ取得手順

1. [SR-NIEL Web計算機](https://www.sr-niel.org/index.php/sr-niel-web-calculators)にアクセス
2. 対象材料（例：シリコン）を選択
3. 粒子種（ProtonまたはElectron）を選択
4. エネルギー範囲を設定して計算を実行
5. 結果をPDF形式でダウンロード

出力されるPDFファイルには、エネルギーとNIEL値の表が含まれています。

## 必要な環境

- Python 3.10以上
- Anaconda（推奨）

## セットアップ

1. Anaconda環境の作成とアクティベート：
```bash
conda create -n sr_niel python=3.10 -y
conda activate sr_niel
```

2. 必要なライブラリのインストール：
```bash
pip install -r requirements.txt
```

または個別にインストール：
```bash
pip install pdfplumber pandas matplotlib numpy
```

## 使用方法

### コマンドライン引数

このツールは、コマンドライン引数としてProtonとElectronのPDFファイルのパスを受け取ります：

```bash
python extract_niel_data.py proton.pdf electron.pdf
```

ファイル名にスペースが含まれる場合は、引用符で囲んでください：

```bash
python extract_niel_data.py "SR-NIEL Results_silicon_proton.pdf" "SR-NIEL Results_silicon_electron.pdf"
```

### 入力ファイル

- **proton.pdf**: ProtonのNIELデータが含まれるPDFファイル
- **electron.pdf**: ElectronのNIELデータが含まれるPDFファイル

PDFファイルは、SR-NIEL Web計算機から取得した結果ファイルである必要があります。ファイルには、エネルギー（MeV）とNIEL値（MeV cm² g⁻¹）の表が含まれている必要があります。

## 計算式

### DDD（Displacement Damage Dose）の計算

DDDは、NIELとフルエンスから計算されます：

```
DDD = NIEL × フルエンス
```

- DDDの単位: MeV/g
- NIELの単位: MeV cm²/g
- フルエンスの単位: cm⁻²

### 欠陥数密度の計算（NRTモデル）

DDDから欠陥数密度を計算します（NRTモデル：Norgett-Robinson-Torrensモデル）：

```
欠陥数密度 (cm⁻³) = (DDD × ρ × η) / (2 × Ed)
```

ここで：
- DDD: Displacement Damage Dose (MeV/g)
- ρ: 材料の密度 (g/cm³) - シリコンの場合、2.33 g/cm³
- η: 欠陥生成効率 - NRTモデルの場合、0.8
- Ed: はじき出ししきい値 (eV) - シリコンの場合、25 eV
- 2Ed: 1 Frenkelペア生成に必要なエネルギー

### 欠陥生成率の計算

欠陥生成率は、欠陥数密度をフルエンスで割った値です：

```
欠陥生成率 (cm⁻¹) = 欠陥数密度 / フルエンス
```

欠陥生成率は、1粒子あたりに生成される欠陥数密度を表す指標で、フルエンスに依存しない特性値です。

## 出力ファイル

スクリプトを実行すると、以下のファイルが生成されます：

### NIELデータ

- `niel_proton.csv` - ProtonのNIELデータ（CSV形式）
- `niel_electron.csv` - ElectronのNIELデータ（CSV形式）
- `niel_plot.png` - ProtonとElectronのNIEL値を比較したグラフ（PNG形式）

### 欠陥数密度データ

- `defect_density_proton.csv` - Protonの欠陥数密度データ（CSV形式）
- `defect_density_electron.csv` - Electronの欠陥数密度データ（CSV形式）
- `defect_density_plot.png` - 欠陥数密度のグラフ（PNG形式）

### 欠陥生成率データ

- `defect_generation_rate_proton.csv` - Protonの欠陥生成率データ（CSV形式）
- `defect_generation_rate_electron.csv` - Electronの欠陥生成率データ（CSV形式）
- `defect_generation_rate_plot.png` - 欠陥生成率のグラフ（PNG形式）

### CSVファイルの形式

各CSVファイルには以下の列が含まれます：

**NIELデータ:**
- `Energy (MeV)` - 粒子のエネルギー（MeV）
- `NIEL (MeV cm^2 g^-1)` - 非電離エネルギー損失（MeV cm² g⁻¹）

**欠陥数密度データ:**
- `Energy (MeV)` - 粒子のエネルギー（MeV）
- `Defect Density (cm^-3)` - 欠陥数密度（cm⁻³）

**欠陥生成率データ:**
- `Energy (MeV)` - 粒子のエネルギー（MeV）
- `Defect Generation Rate (cm^-1)` - 欠陥生成率（cm⁻¹）

### グラフの説明

すべてのグラフは以下の特徴を持ちます：
- X軸: エネルギー（MeV、対数スケール）
- Y軸: 各物理量（対数スケール）
- Protonデータ: 赤い線とマーカー（○）
- Electronデータ: 青い線とマーカー（□）
- メイン・サブ補助線: 点線スタイルで表示

## シリコンの計算結果サンプル

以下に、シリコン（Si）に対する計算結果のサンプルを示します。これらの結果は、SR-NIEL Web計算機から取得したデータを使用し、フルエンス1×10¹⁴ cm⁻²で計算したものです。

### NIEL値の比較

![NIEL Plot](niel_plot.png)

ProtonとElectronのNIEL値をエネルギーに対してプロットしたグラフです。Protonは低エネルギー領域で高いNIEL値を示し、Electronは全体的に低いNIEL値を持ちます。

### 欠陥数密度

![Defect Density Plot](defect_density_plot.png)

放射線照射量1×10¹⁴ cm⁻²での欠陥数密度をエネルギーに対してプロットしたグラフです。Protonは低エネルギー領域で非常に高い欠陥数密度（最大約2.1×10¹⁹ cm⁻³）を示します。

### 欠陥生成率

![Defect Generation Rate Plot](defect_generation_rate_plot.png)

1粒子あたりの欠陥生成率をエネルギーに対してプロットしたグラフです。欠陥生成率はフルエンスに依存しない特性値で、Protonは最大約2.1×10⁵ cm⁻¹、Electronは最大約4.95 cm⁻¹の値を示します。

## 注意事項

- PDFファイルの構造によっては、データの抽出がうまくいかない場合があります
- その場合は、PDFの表形式を確認し、必要に応じてスクリプトを調整してください
- 抽出されたデータは自動的に重複除去とソートが行われます
- 欠陥数密度の計算はNRTモデルに基づいており、シリコンの標準パラメータ（密度2.33 g/cm³、Ed=25 eV、η=0.8）を使用しています
- より正確な計算が必要な場合は、材料特性に応じてパラメータを調整してください

## トラブルシューティング

### PDFからデータが抽出できない場合

1. PDFファイルが正しく配置されているか確認してください
2. PDFファイルが破損していないか確認してください
3. PDFの表形式が標準的な形式か確認してください
4. SR-NIEL Web計算機から取得したPDFファイルであることを確認してください

### グラフが正しく表示されない場合

1. データが正しく抽出されているかCSVファイルを確認してください
2. データに異常値がないか確認してください
3. matplotlibが正しくインストールされているか確認してください

### 計算結果が異常な値になる場合

1. フルエンスの値が正しいか確認してください（デフォルト: 1×10¹⁴ cm⁻²）
2. 材料パラメータ（密度、Ed、η）が適切か確認してください
3. NIELデータが正しく抽出されているか確認してください

## 参考文献

### SR-NIEL関連

- **SR-NIEL公式サイト**: [https://www.sr-niel.org/index.php](https://www.sr-niel.org/index.php)
  - SR-NIEL–7 (version 11.0) - Screened Relativistic (SR) Treatment for NIEL Dose
  - Nuclear and Electronic Stopping Power Calculator
  - ASI (Italian Space Agency) Supported Irradiation Facilities (ASIF) の枠組みでサポートされています

- **SR-NIEL Web計算機**: [https://www.sr-niel.org/index.php/sr-niel-web-calculators](https://www.sr-niel.org/index.php/sr-niel-web-calculators)
  - 電子、陽子、イオン、中性子のNIELおよびTNID（Total Non-Ionizing Energy Loss）線量計算機
  - 単一粒子およびスペクトルフルエンス用の計算機が利用可能

- **SR-NIEL Physics Handbook**: SR-NIELフレームワークの物理ハンドブック
  - 置換損傷の物理、電子阻止能、制限エネルギー損失、TID線量などに関する詳細情報

### 関連プロジェクト

- **GitHub: solar_cell_radiation_damage_analysis_using_phits**: [https://github.com/shirokawakita/solar_cell_radiation_damage_analysis_using_phits](https://github.com/shirokawakita/solar_cell_radiation_damage_analysis_using_phits)
  - DDDから欠陥数密度への換算式の参考
  - PHITSを使用した太陽電池の放射線損傷解析

### SR-NIELの引用文献

SR-NIELの理論的基盤については、以下の文献を参照してください：

- Baur et al. (2014) - Screened relativistic (SR) NIELの表記法の導入
- Leroy and Rancoita (2016) - Sects. 2.2.1–2.2.2, 2.4.2–2.4.3, 7.1.1.6, 7.1.1.8, 11.3.1, 11.3.2で議論

詳細な参考文献リストは、[SR-NIEL公式サイトのbibliographyページ](https://www.sr-niel.org/index.php)を参照してください。

## ライセンス

このツールはSR-NIELの結果ファイルを解析するためのユーティリティです。SR-NIELの利用については、[SR-NIEL公式サイト](https://www.sr-niel.org/index.php)の利用規約を参照してください。
