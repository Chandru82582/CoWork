from sqlalchemy import case, func

from database import Customer, TelecomPartner, get_db
from schemas import ChurnSummaryMetrics, ChurnSummaryResponse, CustomerResponse, PartnerChurnBreakdown


def get_customer_by_id(customer_id: int):
    db = next(get_db())
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()

    if not customer:
        return None

    return CustomerResponse(
        customer_id=customer.customer_id,
        gender=customer.gender,
        age=customer.age,
        pincode=customer.pincode,
        date_of_registration=customer.date_of_registration.strftime("%Y-%m-%d") if customer.date_of_registration else None,
        num_dependents=customer.num_dependents,
        estimated_salary=float(customer.estimated_salary) if customer.estimated_salary is not None else None,
        churn=customer.churn,
    )


def get_churn_summary():
    db = next(get_db())

    overall_stats = (
        db.query(
            func.count(Customer.customer_id).label("total_customers"),
            func.sum(case((Customer.churn.is_(True), 1), else_=0)).label("churned_customers"),
        )
        .one()
    )

    total_customers = overall_stats.total_customers or 0
    churned_customers = overall_stats.churned_customers or 0
    retained_customers = total_customers - churned_customers

    churn_rate = round((churned_customers / total_customers) * 100, 2) if total_customers else 0.0
    retention_rate = round((retained_customers / total_customers) * 100, 2) if total_customers else 0.0

    partner_rows = (
        db.query(
            TelecomPartner.partner_name.label("partner_name"),
            func.count(Customer.customer_id).label("total_customers"),
            func.sum(case((Customer.churn.is_(True), 1), else_=0)).label("churned_customers"),
        )
        .join(TelecomPartner, Customer.telecom_partner_id == TelecomPartner.partner_id)
        .group_by(TelecomPartner.partner_name)
        .all()
    )

    partner_breakdown = [
        PartnerChurnBreakdown(
            partner_name=partner_name,
            total_customers=int(total),
            churned_customers=int(churned or 0),
            churn_rate=round((int(churned or 0) / int(total)) * 100, 2) if total else 0.0,
        )
        for partner_name, total, churned in partner_rows
    ]

    return ChurnSummaryResponse(
        summary=ChurnSummaryMetrics(
            total_customers=total_customers,
            churned_customers=churned_customers,
            churn_rate=churn_rate,
            retained_customers=retained_customers,
            retention_rate=retention_rate,
        ),
        partner_breakdown=partner_breakdown,
    )
