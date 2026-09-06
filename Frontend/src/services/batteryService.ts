export const batteryService = { project: (soc: number, energy: number, soh: number) => Math.max(0, Math.round(soc - energy * (100 / Math.max(55, soh)))) };
