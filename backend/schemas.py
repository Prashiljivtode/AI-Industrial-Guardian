from pydantic import BaseModel, Field
class MachineIn(BaseModel):
    machine_id:str=Field(min_length=1,max_length=64)
    machine_type:str="Industrial Machine"
    temp:float
    vibration:float
    pressure:float
class MaintenanceIn(BaseModel):
    machine_id:str; issue:str; action:str; team:str="Maintenance"; cost:float=0; status:str="PLANNED"
class ChatIn(BaseModel): query:str
class TelemetryIn(BaseModel):
    temp:float; vibration:float; pressure:float

class BulkTelemetryIn(BaseModel):
    machine_id:str
    temp:float
    vibration:float
    pressure:float
