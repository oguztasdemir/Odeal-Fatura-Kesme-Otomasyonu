# Gateway file re-exporting modules to preserve backward compatibility for server.py

from .automation_core import (
    get_or_create_driver,
    find_element_safe,
    init_chrome_driver,
    wait_for_download_complete,
    handle_error
)

from .automation_login import (
    login_process_thread,
    submit_code_thread,
    close_announcement_popup
)

from .automation_invoice import (
    prepare_process_thread,
    try_quick_search,
    long_registration,
    invoice_settings,
    on_prep_finished,
    map_unit,
    process_products_thread
)

from .automation_download import (
    download_invoices_thread
)

from .automation_sync import (
    sync_customers_thread
)

from .automation_queue import (
    process_queue_thread
)
