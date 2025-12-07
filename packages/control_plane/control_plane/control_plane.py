

class PlanStep(BaseModel):
    action: str
    parameters: dict
    context: dict | None
