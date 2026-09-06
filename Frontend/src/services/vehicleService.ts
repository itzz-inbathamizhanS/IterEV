import vehicles from "@/data/vehicles.json";
export const vehicleService = { getAll: () => vehicles, getById: (id: string) => vehicles.find((vehicle) => vehicle.id === id) };
