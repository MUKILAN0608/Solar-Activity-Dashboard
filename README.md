# Solar Activity Dashboard

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Dash](https://img.shields.io/badge/Dash-2.0+-00ADD8?style=flat-square&logo=plotly&logoColor=white)](https://dash.plotly.com/)
[![Plotly](https://img.shields.io/badge/Plotly-5.0+-3F4F75?style=flat-square&logo=plotly&logoColor=white)](https://plotly.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**A sophisticated web-based platform for real-time analysis and visualization of solar phenomena**

[Overview](#overview) • [Key Features](#key-features) • [Installation](#installation) • [Documentation](#documentation) • [Contributing](#contributing)

---

</div>

## Overview

The Solar Activity Dashboard is a comprehensive analytical tool designed for researchers, educators, and space weather enthusiasts to explore and understand solar dynamics. Built with modern web technologies, this platform provides interactive visualizations of solar flare events and sunspot activity patterns, enabling data-driven insights into our Sun's behavior.

### Target Applications

- **Space Weather Research**: Analyze correlations between solar events and geomagnetic activity
- **Educational Demonstrations**: Interactive teaching tool for solar physics concepts
- **Predictive Analysis**: Historical trend identification for forecasting solar cycles
- **Data Exploration**: Rapid filtering and visualization of large solar datasets

---

## Key Features

### Advanced Visualization Engine
Leverage Plotly's interactive charting capabilities with real-time data manipulation, supporting zoom, pan, export, and detailed hover tooltips for comprehensive data exploration.

### Multi-Parameter Solar Flare Analysis
Track and filter solar flares across three intensity classifications (X-class, M-class, C-class) with temporal correlation to sunspot activity, providing insights into solar magnetic field dynamics.

### Temporal Data Filtering
Precision date range selection enables focused analysis on specific solar events, cycles, or historical periods of interest.

### Sunspot Activity Monitoring
Visualize sunspot number variations over time to identify solar cycle patterns, minimum/maximum phases, and anomalous activity periods.

### Responsive Architecture
Modern, mobile-friendly interface built with Bootstrap components ensures optimal user experience across desktop, tablet, and mobile platforms.

### Performance Optimization
Efficient data processing pipeline handles large datasets with minimal latency, ensuring smooth interaction even with extensive historical records.

---

## Installation

### System Requirements

- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large datasets)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Setup Instructions

**1. Clone Repository**
```bash
git clone https://github.com/MUKILAN0608/Solar-Activity-Dashboard.git
cd Solar-Activity-Dashboard
```

**2. Create Virtual Environment** (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Launch Application**
```bash
python solar_dashboard_ultimate.py
```

**5. Access Dashboard**

Navigate to `http://127.0.0.1:8050` in your web browser.

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Framework** | Python 3.8+ | Core application logic and data processing |
| **Web Framework** | Dash 2.0+ | Interactive web application architecture |
| **Visualization** | Plotly 5.0+ | Dynamic, publication-quality charts |
| **Data Processing** | Pandas 2.0+ | High-performance data manipulation |
| **Numerical Computing** | NumPy 1.24+ | Efficient array operations and calculations |
| **UI Components** | Dash Bootstrap | Responsive, professional interface elements |

---

## Project Architecture

```
Solar-Activity-Dashboard/
│
├── data/
│   ├── solar_flare_data.csv              # Solar flare event records
│   └── sunspot_activity.csv              # Historical sunspot observations
│
├── notebooks/
│   ├── solar_flare_data_analysis.ipynb   # Flare event exploratory analysis
│   └── sunspot_activity_analysis.ipynb   # Sunspot trend analysis
│
├── src/
│   └── solar_dashboard_ultimate.py       # Main application entry point
│
├── requirements.txt                       # Python dependencies
├── LICENSE                                # MIT License
└── README.md                              # Project documentation
```

---

## Data Specifications

### Solar Flare Dataset

Comprehensive records of solar flare events with the following schema:

| Field | Type | Description |
|-------|------|-------------|
| `observation_date` | DateTime | UTC timestamp of flare detection |
| `x_class_flares` | Integer | Count of X-class (extreme) flares |
| `m_class_flares` | Integer | Count of M-class (major) flares |
| `c_class_flares` | Integer | Count of C-class (common) flares |
| `sunspot_count` | Integer | Concurrent sunspot observations |

### Sunspot Activity Dataset

Historical sunspot number time series with metadata:

| Field | Type | Description |
|-------|------|-------------|
| `year` | Integer | Observation year |
| `month` | Integer | Observation month |
| `sunspot_total` | Float | Monthly mean sunspot number |
| `solar_cycle` | Integer | Associated solar cycle number |

---

## Usage Documentation

### Interactive Controls

**Date Range Selection**: Use the calendar picker to define analysis windows, enabling focused investigation of specific solar events or cycles.

**Flare Class Filtering**: Toggle visibility of X, M, and C class flares to isolate events of particular intensity levels.

**Sunspot Range Adjustment**: Set minimum and maximum sunspot thresholds to correlate flare activity with magnetic complexity.

### Visualization Interactions

- **Zoom**: Click and drag to magnify regions of interest
- **Pan**: Hold shift and drag to navigate the plot area
- **Hover Details**: Position cursor over data points for detailed metrics
- **Reset View**: Double-click to restore default zoom level
- **Export**: Use toolbar to download plots in PNG, SVG, or PDF formats

---

## Analysis Capabilities

### Solar Flare Event Analysis

The included Jupyter notebook (`solar_flare_data_analysis.ipynb`) demonstrates:

- Data quality assessment and preprocessing pipelines
- Statistical distribution analysis of flare intensities
- Temporal clustering identification
- Correlation studies with sunspot activity
- Frequency analysis across solar cycle phases

### Sunspot Cycle Investigation

The sunspot analysis notebook (`sunspot_activity_analysis.ipynb`) provides:

- Long-term trend decomposition
- Solar cycle periodicity extraction
- Minimum/maximum phase identification
- Anomaly detection in historical records
- Foundation for predictive modeling approaches

---

## Contributing

Contributions from the community are highly valued. To contribute:

1. Fork the repository to your GitHub account
2. Create a feature branch (`git checkout -b feature/enhancement-name`)
3. Implement changes with appropriate documentation
4. Commit with descriptive messages (`git commit -m 'Add: specific enhancement'`)
5. Push to your fork (`git push origin feature/enhancement-name`)
6. Submit a Pull Request with detailed description

### Development Guidelines

- Follow PEP 8 style conventions for Python code
- Include docstrings for all functions and classes
- Add unit tests for new functionality
- Update documentation to reflect changes
- Ensure backward compatibility where possible

---

## License

This project is distributed under the MIT License, permitting commercial and private use, modification, and distribution. See the [LICENSE](LICENSE) file for complete terms.

---

## Acknowledgments

**Author**: Mukilan  
**GitHub**: [@MUKILAN0608](https://github.com/MUKILAN0608)

### Data Sources

Solar flare and sunspot data sourced from:
- NOAA Space Weather Prediction Center
- Solar Influences Data Analysis Center (SIDC)
- NASA Solar Dynamics Observatory

---

## Roadmap

Future development priorities include:

- **Machine Learning Integration**: Predictive models for solar flare forecasting
- **Real-Time Data Feeds**: Integration with live space weather APIs
- **Enhanced Analytics**: Statistical tests and correlation matrices
- **Export Capabilities**: Automated report generation in multiple formats
- **Multi-Language Support**: Internationalization for global accessibility

---

## Support

For bug reports, feature requests, or technical questions:

- **Issues**: Submit via [GitHub Issues](https://github.com/MUKILAN0608/Solar-Activity-Dashboard/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/MUKILAN0608/Solar-Activity-Dashboard/discussions)
- **Email**: Contact the maintainer through GitHub profile

---

<div align="center">

**Built for the solar physics community with modern web technologies**

[![GitHub Stars](https://img.shields.io/github/stars/MUKILAN0608/Solar-Activity-Dashboard?style=social)](https://github.com/MUKILAN0608/Solar-Activity-Dashboard)
[![GitHub Forks](https://img.shields.io/github/forks/MUKILAN0608/Solar-Activity-Dashboard?style=social)](https://github.com/MUKILAN0608/Solar-Activity-Dashboard)

</div>
