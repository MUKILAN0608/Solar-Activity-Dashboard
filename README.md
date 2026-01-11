# ☀️ Solar Activity Dashboard

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Dash](https://img.shields.io/badge/Dash-2.0+-00ADD8?style=for-the-badge&logo=plotly&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.0+-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=for-the-badge&logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**An interactive dashboard for analyzing solar flare and sunspot activity data**

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Usage](#-usage) • [Data](#-data-sources)

</div>

---

## 🌟 Features

| Feature | Description |
|---------|-------------|
| 📊 **Interactive Visualizations** | Dynamic charts powered by Plotly with zoom, pan, and hover details |
| 🔥 **Solar Flare Analysis** | Track X, M, and C class solar flares with filtering capabilities |
| 🌑 **Sunspot Tracking** | Monitor sunspot counts and activity patterns over time |
| 📅 **Date Range Filtering** | Analyze specific time periods with intuitive date selectors |
| 📈 **Trend Analysis** | Identify patterns and correlations in solar activity data |
| 🎨 **Beautiful UI** | Modern, responsive design with smooth animations |

---

## 🖼️ Demo

<div align="center">

### Dashboard Overview
*Interactive dashboard with real-time filtering and beautiful visualizations*

| Solar Flare Analysis | Sunspot Activity |
|:-------------------:|:----------------:|
| Track flare intensity and frequency | Monitor sunspot patterns over solar cycles |

</div>

---

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/MUKILAN0608/Solar-Activity-Dashboard.git
   cd Solar-Activity-Dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the dashboard**
   ```bash
   python solar_dashboard_ultimate.py
   ```

4. **Open your browser**
   ```
   http://127.0.0.1:8050
   ```

---

## 📦 Dependencies

```txt
dash>=2.0.0
dash-bootstrap-components>=1.0.0
plotly>=5.0.0
pandas>=2.0.0
numpy>=1.24.0
python-dateutil>=2.8.0
```

---

## 📁 Project Structure

```
Solar-Activity-Dashboard/
│
├── 📊 Data Files
│   ├── solar_flare_data .csv          # Raw solar flare data
│   └── sunspot_activity .csv          # Raw sunspot activity data
│
├── 📓 Analysis Notebooks
│   ├── solar_flare_data_analysis.ipynb    # Solar flare EDA & analysis
│   └── sunspot_activity_analysis.ipynb    # Sunspot activity EDA & analysis
│
├── 🎯 Dashboard
│   └── solar_dashboard_ultimate.py    # Main interactive dashboard
│
└── 📄 Documentation
    └── README.md                      # Project documentation
```

---

## 📊 Data Sources

### Solar Flare Data
Contains records of solar flare events with the following attributes:
- **Observation Date** - Date of the recorded event
- **X-Class Flares** - Most intense solar flares
- **M-Class Flares** - Medium intensity flares
- **C-Class Flares** - Common, smaller flares
- **Sunspot Count** - Associated sunspot activity

### Sunspot Activity Data
Historical sunspot observations including:
- **Year/Month** - Time period of observation
- **Total Sunspots** - Count of visible sunspots
- **Solar Cycle Phase** - Position within 11-year solar cycle

---

## 🎮 Usage Guide

### Filtering Data
1. Use the **date range picker** to select specific time periods
2. Filter by **flare class** (X, M, C) to focus on specific intensity levels
3. Adjust **sunspot range** to analyze activity during different periods

### Visualization Options
- **Hover** over data points for detailed information
- **Click and drag** to zoom into specific regions
- **Double-click** to reset the view
- Use the **toolbar** for additional options (download, pan, etc.)

---

## 🔬 Analysis Notebooks

### Solar Flare Analysis (`solar_flare_data_analysis.ipynb`)
- Data cleaning and preprocessing
- Exploratory data analysis
- Flare frequency and intensity patterns
- Correlation with sunspot activity

### Sunspot Analysis (`sunspot_activity_analysis.ipynb`)
- Historical sunspot trends
- Solar cycle identification
- Statistical analysis
- Predictive modeling foundations

---

## 🛠️ Technologies Used

<div align="center">

| Technology | Purpose |
|------------|---------|
| **Python** | Core programming language |
| **Dash** | Web application framework |
| **Plotly** | Interactive visualizations |
| **Pandas** | Data manipulation & analysis |
| **NumPy** | Numerical computations |
| **Bootstrap** | Responsive UI components |

</div>

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. 🍴 Fork the repository
2. 🌿 Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. 💾 Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. 📤 Push to the branch (`git push origin feature/AmazingFeature`)
5. 🔃 Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Mukilan**
- GitHub: [@MUKILAN0608](https://github.com/MUKILAN0608)

---

<div align="center">

### ⭐ Star this repository if you found it helpful!

Made with ❤️ and ☀️

</div>
