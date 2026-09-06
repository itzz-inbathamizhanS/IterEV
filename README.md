# IterEV

> IterEV is a predictive decision engine that optimizes electric vehicle routing by quantifying how today's battery depletion impacts the feasibility of tomorrow's mobility. Unlike traditional algorithms, IterEV introduces Future Mobility Feasibility (FMF) to ensure current routing decisions never compromise your upcoming high-priority EV journeys.

## Overview

IterEV bridges the gap between single-trip routing and long-term battery capability management. The system consists of five core physics and decision engines:
1. **Energy Engine**: Computes route-specific energy consumption under traffic and temperature conditions.
2. **Battery Engine**: Projects immediate and overnight SOC (State of Charge) depletion based on battery health (SOH).
3. **Feasibility Engine**: Quantifies the probability of completing upcoming high-priority journeys.
4. **Optimizer**: Balances the trade-offs between current travel time/cost and future mobility risk.
5. **Explanation Engine**: Generates transparent, human-readable reasoning for the selected decision.

## Project Structure

- **`/Backend`**: The core physics and optimization engines built with Python (FastAPI).
- **`/Frontend`**: The interactive visual interface built with React (Vite + TanStack Router).

## Getting Started

### Backend
```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd Frontend
npm install
npm run dev
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
