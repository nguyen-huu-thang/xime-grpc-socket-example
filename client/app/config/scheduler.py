from xime.starters.scheduler import IntervalJob, SchedulerConfig, configure_scheduler

from app.integration.trust.scheduler.CertRotationJob import CertRotationJob

# Same cert rotation job as the server: the client also holds an mTLS identity
# (it presents a client cert), so it rotates its own cert too. When the cert
# rotates, the outbound dynamic channel rebuilds itself automatically.
# Job rotate cert giống server: client cũng giữ một mTLS identity (xuất trình
# cert client) nên cũng tự rotate cert của mình. Khi cert đổi, channel động chiều
# ra tự rebuild.
configure_scheduler(SchedulerConfig(
    jobs=[
        IntervalJob(job_class=CertRotationJob, hours=1),
    ],
    timezone="UTC",
))
