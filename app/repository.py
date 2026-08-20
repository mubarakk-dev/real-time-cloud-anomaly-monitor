from sqlalchemy import desc, select

from .database import Prediction, Session


async def save_prediction(values: dict) -> Prediction:
    async with Session() as session:
        prediction = Prediction(**values)
        session.add(prediction)
        await session.commit()
        await session.refresh(prediction)
        return prediction


async def recent_predictions(limit: int = 100, anomalies_only: bool = False) -> list[Prediction]:
    statement = select(Prediction).order_by(desc(Prediction.window_end)).limit(limit)
    if anomalies_only:
        statement = statement.where(Prediction.is_anomaly.is_(True))
    async with Session() as session:
        return list((await session.scalars(statement)).all())
