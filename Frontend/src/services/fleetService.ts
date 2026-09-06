import vehicles from "@/data/vehicles.json";
import demand from "@/data/futureDemand.json";
export const fleetService = { getVehicles: () => vehicles, getDemand: () => demand };
