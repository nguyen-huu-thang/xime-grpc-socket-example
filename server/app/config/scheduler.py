from xime.starters.scheduler import IntervalJob, SchedulerConfig, configure_scheduler

from app.integration.trust.scheduler.CertRotationJob import CertRotationJob

# Periodic cert rotation: checks hourly whether the mTLS cert is due to rotate.
# Rotation only updates the resolver; inbound server creds and outbound channels
# pick up the new cert automatically (dynamic mTLS).
# Rotate cert định kỳ: mỗi giờ kiểm tra cert mTLS có tới hạn rotate chưa. Rotate
# chỉ cập nhật resolver; server creds vào và channel ra tự nhặt cert mới (mTLS động).
configure_scheduler(SchedulerConfig(
    jobs=[
        IntervalJob(job_class=CertRotationJob, hours=1),
    ],
    timezone="UTC",
))
