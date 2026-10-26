"""Public-site texts. Every key must define every language in app.i18n.LANGUAGES."""

SERVICE_KEYS = ("elevator_chips", "door_chips", "cctv", "security_systems")

MESSAGES = {
  # Navigation and layout
  "nav.home": {"en": "Home", "ka": "მთავარი"},
  "nav.services": {"en": "Services", "ka": "სერვისები"},
  "nav.about": {"en": "About us", "ka": "ჩვენ შესახებ"},
  "nav.contact": {"en": "Contact", "ka": "კონტაქტი"},
  "nav.login": {"en": "Log in", "ka": "შესვლა"},
  "nav.account": {"en": "My account", "ka": "ჩემი ანგარიში"},
  "nav.menu": {"en": "Menu", "ka": "მენიუ"},
  "nav.language": {"en": "Language", "ka": "ენა"},
  "footer.rights": {"en": "All rights reserved.", "ka": "ყველა უფლება დაცულია."},
  "footer.follow": {"en": "Follow us", "ka": "გამოგვყევით"},

  # Home page
  "home.title": {
    "en": "Smart access and security for your building",
    "ka": "ჭკვიანი დაშვება და უსაფრთხოება თქვენი შენობისთვის",
  },
  "home.subtitle": {
    "en": (
      "We install and maintain elevator chips, entrance door access, CCTV cameras and "
      "digital security systems for residential and commercial buildings."
    ),
    "ka": (
      "ვამონტაჟებთ და ვემსახურებით ლიფტის ჩიპებს, სადარბაზოს კარის დაშვების სისტემებს, "
      "ვიდეოსათვალთვალო კამერებს და ციფრულ უსაფრთხოების სისტემებს საცხოვრებელი და "
      "კომერციული შენობებისთვის."
    ),
  },
  "home.cta_primary": {"en": "Request a consultation", "ka": "მოითხოვეთ კონსულტაცია"},
  "home.cta_secondary": {"en": "Our services", "ka": "ჩვენი სერვისები"},
  "home.services_title": {"en": "What we do", "ka": "რას ვაკეთებთ"},
  "home.why_title": {"en": "Why buildings choose us", "ka": "რატომ გვირჩევენ"},
  "home.why.fast.title": {"en": "Fast installation", "ka": "სწრაფი მონტაჟი"},
  "home.why.fast.text": {
    "en": "Most systems are installed within a few days, with minimal disruption for residents.",
    "ka": "სისტემების უმეტესობას რამდენიმე დღეში ვამონტაჟებთ, მაცხოვრებლებისთვის მინიმალური შეფერხებით.",
  },
  "home.why.support.title": {"en": "Local support", "ka": "ადგილობრივი მხარდაჭერა"},
  "home.why.support.text": {
    "en": "Our own technicians handle maintenance, lost chips and repairs.",
    "ka": "მომსახურებას, დაკარგულ ჩიპებს და შეკეთებას ჩვენი ტექნიკოსები უზრუნველყოფენ.",
  },
  "home.why.fees.title": {"en": "Transparent monthly fees", "ka": "გამჭვირვალე ყოველთვიური გადასახადი"},
  "home.why.fees.text": {
    "en": "One clear monthly fee per door. Residents can check their balance online at any time.",
    "ka": "ერთი მკაფიო ყოველთვიური გადასახადი თითო კარზე. მაცხოვრებლებს ბალანსის ნახვა ნებისმიერ დროს შეუძლიათ.",
  },
  "home.customers_title": {"en": "Already a customer?", "ka": "უკვე ჩვენი მომხმარებელი ხართ?"},
  "home.customers_text": {
    "en": "Log in with your personal ID number to see your balance, chips, subscriptions and payments.",
    "ka": "შედით პირადი ნომრით და ნახეთ ბალანსი, ჩიპები, გამოწერები და გადახდები.",
  },
  "home.learn_more": {"en": "Learn more", "ka": "დაწვრილებით"},

  # Services
  "services.title": {"en": "Our services", "ka": "ჩვენი სერვისები"},
  "services.subtitle": {
    "en": "Design, installation and ongoing maintenance, all from one team.",
    "ka": "პროექტირება, მონტაჟი და მუდმივი მომსახურება — ერთი გუნდისგან.",
  },
  "services.request": {"en": "Request this service", "ka": "მოითხოვეთ ეს სერვისი"},
  "service.elevator_chips.title": {"en": "Elevator chips", "ka": "ლიფტის ჩიპები"},
  "service.elevator_chips.summary": {
    "en": "Chip-based elevator access, so only residents and their guests can use the lift.",
    "ka": "ჩიპით მართვადი ლიფტი — ლიფტით სარგებლობა მხოლოდ მაცხოვრებლებს და მათ სტუმრებს შეუძლიათ.",
  },
  "service.elevator_chips.details": {
    "en": [
      "Chip readers installed in elevator cabins",
      "Chips issued and registered per apartment",
      "Lost chips deactivated immediately",
      "Monthly maintenance and support",
    ],
    "ka": [
      "ჩიპის წამკითხველის მონტაჟი ლიფტის კაბინაში",
      "ჩიპების გაცემა და რეგისტრაცია ბინების მიხედვით",
      "დაკარგული ჩიპის დაუყოვნებლივ გაუქმება",
      "ყოველთვიური მომსახურება და მხარდაჭერა",
    ],
  },
  "service.door_chips.title": {"en": "Security door chips", "ka": "სადარბაზოს კარის ჩიპები"},
  "service.door_chips.summary": {
    "en": "Keyless chip entry for building entrances and security doors.",
    "ka": "უგასაღებო შესვლა სადარბაზოსა და დაცულ კარებში ჩიპის საშუალებით.",
  },
  "service.door_chips.details": {
    "en": [
      "Electromagnetic and electric locks",
      "Chip readers with intercom integration",
      "Access per entrance, floor or door",
      "Fast replacement of lost chips",
    ],
    "ka": [
      "ელექტრომაგნიტური და ელექტრო საკეტები",
      "ჩიპის წამკითხველები დომოფონთან ინტეგრაციით",
      "დაშვება სადარბაზოს, სართულის ან კარის მიხედვით",
      "დაკარგული ჩიპის სწრაფი შეცვლა",
    ],
  },
  "service.cctv.title": {"en": "CCTV cameras", "ka": "ვიდეოსათვალთვალო კამერები"},
  "service.cctv.summary": {
    "en": "HD video surveillance for entrances, yards, parking and commercial spaces.",
    "ka": "მაღალი ხარისხის ვიდეოთვალთვალი სადარბაზოებისთვის, ეზოებისთვის, პარკინგისა და კომერციული ფართებისთვის.",
  },
  "service.cctv.details": {
    "en": [
      "Indoor and outdoor HD cameras with night vision",
      "Recording with secure storage",
      "Live view from your phone",
      "Design, installation and maintenance",
    ],
    "ka": [
      "შიდა და გარე HD კამერები ღამის ხედვით",
      "ჩანაწერების დაცული შენახვა",
      "პირდაპირი ყურება ტელეფონიდან",
      "პროექტირება, მონტაჟი და მომსახურება",
    ],
  },
  "service.security_systems.title": {"en": "Digital security systems", "ka": "ციფრული უსაფრთხოების სისტემები"},
  "service.security_systems.summary": {
    "en": "Alarms, access control and smart locks working together as one system.",
    "ka": "სიგნალიზაცია, დაშვების კონტროლი და ჭკვიანი საკეტები — ერთიან სისტემაში.",
  },
  "service.security_systems.details": {
    "en": [
      "Intrusion and fire alarm systems",
      "Access control for offices and buildings",
      "Smart locks with remote management",
      "Consultation and security audit",
    ],
    "ka": [
      "დაცვითი და სახანძრო სიგნალიზაცია",
      "დაშვების კონტროლი ოფისებისა და შენობებისთვის",
      "ჭკვიანი საკეტები დისტანციური მართვით",
      "კონსულტაცია და უსაფრთხოების აუდიტი",
    ],
  },
  "service.other.title": {"en": "Something else", "ka": "სხვა"},

  # About
  "about.title": {"en": "About us", "ka": "ჩვენ შესახებ"},
  "about.intro": {
    "en": (
      "We are a Tbilisi-based team specialising in access control and security for "
      "apartment buildings, offices and commercial properties."
    ),
    "ka": (
      "ჩვენ ვართ თბილისში დაფუძნებული გუნდი, რომელიც სპეციალიზდება დაშვების კონტროლსა "
      "და უსაფრთხოებაზე საცხოვრებელი კორპუსების, ოფისებისა და კომერციული ობიექტებისთვის."
    ),
  },
  "about.body": {
    "en": (
      "From a single entrance door to a full building system with elevator chips and "
      "cameras, we plan the installation, set everything up, and stay responsible for "
      "maintenance afterwards. Residents pay one monthly fee per door and can follow their "
      "balance and payments online."
    ),
    "ka": (
      "ერთი სადარბაზოს კარიდან დაწყებული, ლიფტის ჩიპებითა და კამერებით აღჭურვილი სრული "
      "სისტემით დამთავრებული — ვგეგმავთ მონტაჟს, ვაწყობთ ყველაფერს და შემდგომ "
      "მომსახურებაზეც ჩვენ ვართ პასუხისმგებელი. მაცხოვრებლები იხდიან ერთ ყოველთვიურ "
      "გადასახადს თითო კარზე და ბალანსსა და გადახდებს ონლაინ ადევნებენ თვალს."
    ),
  },
  "about.values_title": {"en": "How we work", "ka": "როგორ ვმუშაობთ"},
  "about.values": {
    "en": [
      "A free on-site consultation before any installation",
      "Clear pricing agreed in advance",
      "Quick response when something stops working",
    ],
    "ka": [
      "უფასო კონსულტაცია ადგილზე მონტაჟამდე",
      "წინასწარ შეთანხმებული მკაფიო ფასები",
      "სწრაფი რეაგირება, როცა რამე წყვეტს მუშაობას",
    ],
  },

  # Contact
  "contact.title": {"en": "Contact us", "ka": "დაგვიკავშირდით"},
  "contact.subtitle": {
    "en": "Tell us about your building and we will call you back.",
    "ka": "მოგვიყევით თქვენი შენობის შესახებ და დაგიკავშირდებით.",
  },
  "contact.details_title": {"en": "Contact details", "ka": "საკონტაქტო ინფორმაცია"},
  "contact.phone": {"en": "Phone", "ka": "ტელეფონი"},
  "contact.email": {"en": "Email", "ka": "ელ. ფოსტა"},
  "contact.address": {"en": "Address", "ka": "მისამართი"},
  "contact.hours": {"en": "Working hours", "ka": "სამუშაო საათები"},
  "contact.open_map": {"en": "Open in map", "ka": "რუკაზე ნახვა"},
  "contact.form_title": {"en": "Send us a message", "ka": "მოგვწერეთ"},
  "contact.field.name": {"en": "Your name", "ka": "თქვენი სახელი"},
  "contact.field.phone": {"en": "Phone number", "ka": "ტელეფონის ნომერი"},
  "contact.field.email": {"en": "Email (optional)", "ka": "ელ. ფოსტა (არასავალდებულო)"},
  "contact.field.service": {"en": "What are you interested in?", "ka": "რა გაინტერესებთ?"},
  "contact.field.message": {"en": "Message", "ka": "შეტყობინება"},
  "contact.field.message_hint": {
    "en": "For example: address of the building, number of entrances or apartments.",
    "ka": "მაგალითად: შენობის მისამართი, სადარბაზოების ან ბინების რაოდენობა.",
  },
  "contact.submit": {"en": "Send", "ka": "გაგზავნა"},
  "contact.success": {
    "en": "Thank you! We received your request and will contact you soon.",
    "ka": "გმადლობთ! თქვენი მოთხოვნა მიღებულია, მალე დაგიკავშირდებით.",
  },
  "contact.error.form": {"en": "Please fix the highlighted fields.", "ka": "გთხოვთ, გაასწოროთ მონიშნული ველები."},
  "contact.error.name": {"en": "Please enter your name.", "ka": "გთხოვთ, მიუთითოთ სახელი."},
  "contact.error.phone": {"en": "Please enter a valid phone number.", "ka": "გთხოვთ, მიუთითოთ სწორი ტელეფონის ნომერი."},
  "contact.error.email": {"en": "Please enter a valid email address.", "ka": "გთხოვთ, მიუთითოთ სწორი ელ. ფოსტა."},
  "contact.error.service": {"en": "Please choose a service.", "ka": "გთხოვთ, აირჩიოთ სერვისი."},
  "contact.error.message": {
    "en": "Please write a message of at least 10 characters.",
    "ka": "გთხოვთ, დაწეროთ შეტყობინება მინიმუმ 10 სიმბოლოთი.",
  },
  "contact.too_many": {
    "en": "You have sent several requests already. Please call us or try again later.",
    "ka": "თქვენ უკვე გამოგზავნეთ რამდენიმე მოთხოვნა. გთხოვთ, დაგვირეკოთ ან სცადოთ მოგვიანებით.",
  },

  "error.not_found": {"en": "This page does not exist.", "ka": "ეს გვერდი არ არსებობს."},

  # Login
  "login.title": {"en": "Sign in", "ka": "შესვლა"},
  "login.subtitle": {
    "en": "Sign in with your 11-digit personal ID number and password.",
    "ka": "შედით 11-ნიშნა პირადი ნომრით და პაროლით.",
  },
  "login.id_number": {"en": "Personal ID number", "ka": "პირადი ნომერი"},
  "login.password": {"en": "Password", "ka": "პაროლი"},
  "login.submit": {"en": "Sign in", "ka": "შესვლა"},
  "login.forgot": {
    "en": "Forgot your password? Contact us and we will reset it for you.",
    "ka": "დაგავიწყდათ პაროლი? დაგვიკავშირდით და აღგიდგენთ.",
  },
  "login.invalid": {"en": "Invalid ID number or password.", "ka": "პირადი ნომერი ან პაროლი არასწორია."},
  "login.suspended": {
    "en": "Your account is suspended. Please contact us.",
    "ka": "თქვენი ანგარიში შეჩერებულია. გთხოვთ, დაგვიკავშირდეთ.",
  },
  "login.required": {"en": "Please log in to continue.", "ka": "გასაგრძელებლად გთხოვთ, შეხვიდეთ სისტემაში."},
  "login.too_many": {
    "en": "Too many attempts. Please wait a few minutes and try again.",
    "ka": "ძალიან ბევრი მცდელობა. გთხოვთ, დაელოდოთ რამდენიმე წუთს და სცადოთ თავიდან.",
  },

  # Shared dashboard chrome
  "common.cancel": {"en": "Cancel", "ka": "გაუქმება"},
  "common.save": {"en": "Save", "ka": "შენახვა"},
  "common.save_changes": {"en": "Save changes", "ka": "ცვლილებების შენახვა"},
  "common.delete": {"en": "Delete", "ka": "წაშლა"},
  "common.edit": {"en": "Edit", "ka": "რედაქტირება"},
  "common.search": {"en": "Search...", "ka": "ძიება..."},
  "common.clear": {"en": "Clear", "ka": "გასუფთავება"},
  "common.previous": {"en": "Previous", "ka": "წინა"},
  "common.next": {"en": "Next", "ka": "შემდეგი"},
  "common.page_of": {"en": "Page {page} of {pages} · {total} total", "ka": "გვერდი {page} / {pages} · სულ {total}"},
  "common.open": {"en": "Open", "ka": "გახსნა"},
  "common.view_all": {"en": "View all", "ka": "ყველას ნახვა"},
  "common.menu": {"en": "Menu", "ka": "მენიუ"},
  "common.sign_out": {"en": "Sign out", "ka": "გამოსვლა"},
  "common.view_website": {"en": "View website", "ka": "საიტზე გადასვლა"},
  "common.apply": {"en": "Apply", "ka": "გამოყენება"},
  "common.empty": {"en": "Nothing to show yet.", "ka": "საჩვენებელი ჯერ არ არის."},

  "status.active": {"en": "active", "ka": "აქტიური"},
  "status.inactive": {"en": "inactive", "ka": "არააქტიური"},
  "status.suspended": {"en": "suspended", "ka": "შეჩერებული"},
  "status.overdue": {"en": "overdue", "ka": "ვადაგადაცილებული"},
  "status.payment": {"en": "payment", "ka": "გადახდა"},
  "status.fee": {"en": "fee", "ka": "საკომისიო"},
  "status.adjustment": {"en": "adjustment", "ka": "კორექტირება"},
  "status.refund": {"en": "refund", "ka": "დაბრუნება"},
  "status.pending": {"en": "pending", "ka": "მოლოდინში"},
  "status.completed": {"en": "completed", "ka": "დასრულებული"},
  "status.failed": {"en": "failed", "ka": "წარუმატებელი"},
  "status.cancelled": {"en": "cancelled", "ka": "გაუქმებული"},
  "status.new": {"en": "new", "ka": "ახალი"},
  "status.in_progress": {"en": "in progress", "ka": "მუშავდება"},
  "status.done": {"en": "done", "ka": "დასრულებული"},
  "status.spam": {"en": "spam", "ka": "სპამი"},
  "status.matched": {"en": "matched", "ka": "შესაბამისობაში"},
  "status.unmatched": {"en": "unmatched", "ka": "შეუსაბამო"},
  "status.skipped": {"en": "skipped", "ka": "გამოტოვებული"},
  "status.duplicate": {"en": "duplicate", "ka": "დუბლიკატი"},
  "status.door_reference": {"en": "door reference", "ka": "კარის კოდი"},
  "status.uid_token": {"en": "uid token", "ka": "uid ტოკენი"},
  "status.partner_tax_code": {"en": "tax code", "ka": "საიდენტიფიკაციო კოდი"},
  "status.partner_name_id": {"en": "name ID", "ka": "სახელის ID"},
  "status.manual": {"en": "manual", "ka": "ხელით"},

  "nav.admin": {"en": "Admin", "ka": "ადმინი"},
  "nav.admin.dashboard": {"en": "Dashboard", "ka": "მიმოხილვა"},
  "nav.admin.users": {"en": "Users", "ka": "მომხმარებლები"},
  "nav.admin.buildings": {"en": "Buildings", "ka": "შენობები"},
  "nav.admin.subscriptions": {"en": "Subscriptions", "ka": "გამოწერები"},
  "nav.admin.chips": {"en": "Chips", "ka": "ჩიპები"},
  "nav.admin.transactions": {"en": "Transactions", "ka": "ტრანზაქციები"},
  "nav.admin.logs": {"en": "Logs", "ka": "ჟურნალი"},
  "nav.admin.import": {"en": "Import payments", "ka": "გადახდების იმპორტი"},
  "nav.admin.unmatched": {"en": "Unmatched", "ka": "შეუსაბამო"},
  "nav.admin.inquiries": {"en": "Inquiries", "ka": "მოთხოვნები"},
  "nav.user.section": {"en": "My account", "ka": "ჩემი ანგარიში"},
  "nav.user.dashboard": {"en": "Dashboard", "ka": "მიმოხილვა"},
  "nav.user.subscriptions": {"en": "Subscriptions", "ka": "გამოწერები"},
  "nav.user.chips": {"en": "Chips", "ka": "ჩიპები"},
  "nav.user.transactions": {"en": "Payments", "ka": "გადახდები"},
  "nav.user.pay": {"en": "How to pay", "ka": "როგორ გადავიხადო"},
  "nav.user.profile": {"en": "Profile", "ka": "პროფილი"},

  "col.date": {"en": "Date", "ka": "თარიღი"},
  "col.type": {"en": "Type", "ka": "ტიპი"},
  "col.amount": {"en": "Amount", "ka": "თანხა"},
  "col.status": {"en": "Status", "ka": "სტატუსი"},
  "col.description": {"en": "Description", "ka": "აღწერა"},
  "col.reference": {"en": "Reference", "ka": "რეფერენსი"},
  "col.building": {"en": "Building", "ka": "შენობა"},
  "col.door": {"en": "Door", "ka": "კარი"},
  "col.payment_reference": {"en": "Payment reference", "ka": "გადახდის კოდი"},
  "col.monthly_fee": {"en": "Monthly fee", "ka": "ყოველთვიური"},
  "col.next_due": {"en": "Next payment due", "ka": "შემდეგი გადახდა"},
  "col.chip": {"en": "Chip number", "ka": "ჩიპის ნომერი"},
  "col.assigned": {"en": "Assigned", "ka": "მინიჭებული"},
  "col.deactivated": {"en": "Deactivated", "ka": "გაუქმებული"},
  "col.name": {"en": "Name", "ka": "სახელი"},
  "col.phone": {"en": "Phone", "ka": "ტელეფონი"},
  "col.email": {"en": "Email", "ka": "ელ. ფოსტა"},
  "col.service": {"en": "Service", "ka": "სერვისი"},
  "col.received": {"en": "Received", "ka": "მიღებული"},

  "field.id_number": {"en": "ID number", "ka": "პირადი ნომერი"},
  "field.phones": {"en": "Phone numbers", "ka": "ტელეფონის ნომრები"},
  "field.email": {"en": "Email", "ka": "ელ. ფოსტა"},
  "field.name": {"en": "Name", "ka": "სახელი"},
  "field.balance": {"en": "Balance", "ka": "ბალანსი"},
  "field.status": {"en": "Status", "ka": "სტატუსი"},

  # User portal
  "user.dash.title": {"en": "My dashboard", "ka": "ჩემი ანგარიში"},
  "user.dash.subtitle": {
    "en": "Account balance, subscriptions, and recent activity.",
    "ka": "ბალანსი, გამოწერები და ბოლო აქტივობა.",
  },
  "user.dash.balance": {"en": "Balance", "ka": "ბალანსი"},
  "user.dash.fees": {"en": "Monthly fees", "ka": "ყოველთვიური"},
  "user.dash.subscriptions": {"en": "Subscriptions", "ka": "გამოწერები"},
  "user.dash.chips": {"en": "Active chips", "ka": "აქტიური ჩიპები"},
  "user.dash.overdue": {"en": "Overdue", "ka": "ვადაგადაცილებული"},
  "user.dash.profile": {"en": "Profile", "ka": "პროფილი"},
  "user.dash.recent": {"en": "Recent transactions", "ka": "ბოლო ტრანზაქციები"},
  "user.dash.no_txn": {"en": "No transactions yet.", "ka": "ტრანზაქციები ჯერ არ არის."},

  "user.subs.title": {"en": "My subscriptions", "ka": "ჩემი გამოწერები"},
  "user.subs.subtitle": {
    "en": "Door-level billing for your buildings.",
    "ka": "კარის გადასახადი თქვენს შენობებში.",
  },
  "user.subs.heading": {"en": "Your subscriptions", "ka": "თქვენი გამოწერები"},
  "user.subs.count": {"en": "{n} subscriptions", "ka": "{n} გამოწერა"},
  "user.subs.empty": {"en": "You have no subscriptions.", "ka": "გამოწერები არ გაქვთ."},

  "user.chips.title": {"en": "My chips", "ka": "ჩემი ჩიპები"},
  "user.chips.subtitle": {
    "en": "Physical access chips assigned to your account.",
    "ka": "თქვენს ანგარიშზე მინიჭებული ჩიპები.",
  },
  "user.chips.heading": {"en": "Your chips", "ka": "თქვენი ჩიპები"},
  "user.chips.count": {"en": "{n} chips", "ka": "{n} ჩიპი"},
  "user.chips.empty": {"en": "You have no chips assigned.", "ka": "ჩიპები მინიჭებული არ არის."},

  "user.txn.title": {"en": "Payment history", "ka": "გადახდების ისტორია"},
  "user.txn.subtitle": {
    "en": "All credits and charges on your account.",
    "ka": "ანგარიშზე ყველა ჩარიცხვა და ჩამოჭრა.",
  },
  "user.txn.heading": {"en": "Your transactions", "ka": "თქვენი ტრანზაქციები"},
  "user.txn.count": {"en": "{n} transactions", "ka": "{n} ტრანზაქცია"},
  "user.txn.empty": {"en": "No transactions yet.", "ka": "ტრანზაქციები ჯერ არ არის."},

  "user.profile.title": {"en": "Profile", "ka": "პროფილი"},
  "user.profile.subtitle": {"en": "Your account details.", "ka": "თქვენი ანგარიშის დეტალები."},
  "user.profile.change_password": {"en": "Change password", "ka": "პაროლის შეცვლა"},

  "user.password.title": {"en": "Change password", "ka": "პაროლის შეცვლა"},
  "user.password.subtitle": {"en": "Update your account password.", "ka": "განაახლეთ ანგარიშის პაროლი."},
  "user.password.current": {"en": "Current password", "ka": "მიმდინარე პაროლი"},
  "user.password.new": {"en": "New password", "ka": "ახალი პაროლი"},
  "user.password.submit": {"en": "Update password", "ka": "პაროლის განახლება"},
  "user.password.updated": {
    "en": "Password updated. You have been signed out on other devices.",
    "ka": "პაროლი განახლდა. სხვა მოწყობილობებიდან გამოხვედით.",
  },
  "user.inactive": {
    "en": "Your account is not active. Please contact us.",
    "ka": "თქვენი ანგარიში არ არის აქტიური. გთხოვთ, დაგვიკავშირდეთ.",
  },

  "user.pay.title": {"en": "How to pay", "ka": "როგორ გადავიხადო"},
  "user.pay.subtitle": {
    "en": "Transfer to our bank account and put your payment reference in the description.",
    "ka": "გადმორიცხეთ ჩვენს ანგარიშზე და დანიშნულებაში მიუთითეთ თქვენი გადახდის კოდი.",
  },
  "user.pay.recipient": {"en": "Recipient", "ka": "მიმღები"},
  "user.pay.accounts": {"en": "Bank accounts", "ka": "საბანკო ანგარიშები"},
  "user.pay.iban": {"en": "IBAN", "ka": "IBAN"},
  "user.pay.bank": {"en": "Bank", "ka": "ბანკი"},
  "user.pay.your_refs": {"en": "Your payment references", "ka": "თქვენი გადახდის კოდები"},
  "user.pay.refs_help": {
    "en": "Put the code of the door you are paying for in the transfer description. For several doors, write them separated by commas.",
    "ka": "გადარიცხვის დანიშნულებაში მიუთითეთ იმ კარის კოდი, რომლისთვისაც იხდით. რამდენიმე კარზე გადახდისას კოდები ჩაწერეთ მძიმით.",
  },
  "user.pay.example": {
    "en": "Example: {code}",
    "ka": "მაგალითი: {code}",
  },
  "user.pay.fallback": {
    "en": "If you leave the description empty, we still try to match the payment by your personal ID number.",
    "ka": "თუ დანიშნულებას ცარიელს დატოვებთ, გადახდას თქვენი პირადი ნომრით შევუსაბამებთ.",
  },
  "user.pay.empty": {
    "en": "You have no subscriptions yet, so there is no payment reference to show.",
    "ka": "გამოწერები ჯერ არ გაქვთ, ამიტომ გადახდის კოდი არ ჩანს.",
  },
  "user.pay.no_banks": {
    "en": "Bank details are not configured yet. Please contact us to pay.",
    "ka": "საბანკო რეკვიზიტები ჯერ არ არის მითითებული. გადახდისთვის დაგვიკავშირდით.",
  },

  # Admin page titles
  "admin.dash.title": {"en": "Dashboard", "ka": "მიმოხილვა"},
  "admin.dash.subtitle": {
    "en": "Overview of users, payments, and recent activity.",
    "ka": "მომხმარებლები, გადახდები და ბოლო აქტივობა.",
  },
  "admin.dash.users": {"en": "Users", "ka": "მომხმარებლები"},
  "admin.dash.buildings": {"en": "Buildings", "ka": "შენობები"},
  "admin.dash.unmatched": {"en": "Unmatched payments", "ka": "შეუსაბამო გადახდები"},
  "admin.dash.unmatched_heading": {"en": "Unmatched bank payments", "ka": "შეუსაბამო საბანკო გადახდები"},
  "admin.dash.unmatched_help": {
    "en": "These incoming payments could not be linked to a registered user.",
    "ka": "ეს შემოსული გადახდები რეგისტრირებულ მომხმარებელს ვერ მივაბით.",
  },
  "admin.dash.review": {"en": "Review all", "ka": "ყველას ნახვა"},
  "admin.users.title": {"en": "Users", "ka": "მომხმარებლები"},
  "admin.users.subtitle": {"en": "Register residents and manage accounts.", "ka": "მაცხოვრებლების რეგისტრაცია და ანგარიშები."},
  "admin.users.edit": {"en": "Edit user", "ka": "მომხმარებლის რედაქტირება"},
  "admin.users.edit_sub": {"en": "Update resident account details.", "ka": "მაცხოვრებლის ანგარიშის განახლება."},
  "admin.buildings.title": {"en": "Buildings", "ka": "შენობები"},
  "admin.buildings.subtitle": {"en": "Manage building registry for subscriptions.", "ka": "შენობების რეესტრი გამოწერებისთვის."},
  "admin.buildings.edit": {"en": "Edit building", "ka": "შენობის რედაქტირება"},
  "admin.buildings.edit_sub": {"en": "Update building registry details.", "ka": "შენობის მონაცემების განახლება."},
  "admin.subs.title": {"en": "Subscriptions", "ka": "გამოწერები"},
  "admin.subs.subtitle": {"en": "Door-level billing subscriptions for residents.", "ka": "კარის გამოწერები მაცხოვრებლებისთვის."},
  "admin.subs.edit": {"en": "Edit subscription", "ka": "გამოწერის რედაქტირება"},
  "admin.subs.edit_sub": {"en": "Update door subscription and billing details.", "ka": "კარის გამოწერისა და ბილინგის განახლება."},
  "admin.chips.title": {"en": "Chips", "ka": "ჩიპები"},
  "admin.chips.subtitle": {"en": "Assign and manage physical access chips.", "ka": "ფიზიკური ჩიპების მინიჭება და მართვა."},
  "admin.txn.title": {"en": "Transactions", "ka": "ტრანზაქციები"},
  "admin.txn.subtitle": {"en": "All ledger entries with admin filtering.", "ka": "ყველა ჩანაწერი ფილტრებით."},
  "admin.logs.title": {"en": "Application logs", "ka": "აპლიკაციის ჟურნალი"},
  "admin.import.title": {"en": "Import bank payments", "ka": "საბანკო გადახდების იმპორტი"},
  "admin.import.subtitle": {
    "en": "Upload a CSV export from TBC, BoG, or compatible Georgian bank format.",
    "ka": "ატვირთეთ TBC, საქართველოს ბანკის ან თავსებადი CSV.",
  },
  "admin.unmatched.title": {"en": "Unmatched payments", "ka": "შეუსაბამო გადახდები"},
  "admin.unmatched.subtitle": {
    "en": "Review incoming bank transfers that could not be matched automatically.",
    "ka": "გადახდები, რომლებიც ავტომატურად ვერ შეესაბამება.",
  },
  "admin.inquiries.title": {"en": "Inquiries", "ka": "მოთხოვნები"},
  "admin.inquiries.subtitle": {
    "en": "Requests sent through the contact form on the public website.",
    "ka": "საჯარო საიტის საკონტაქტო ფორმიდან გამოგზავნილი მოთხოვნები.",
  },
  "admin.inquiries.open": {"en": "Inquiry #{id}", "ka": "მოთხოვნა #{id}"},
  "admin.inquiries.received": {"en": "Received {when}", "ka": "მიღებულია {when}"},
  "admin.inquiries.empty": {"en": "No inquiries found.", "ka": "მოთხოვნები არ მოიძებნა."},
  "admin.inquiries.search": {
    "en": "Search name, phone, email, message...",
    "ka": "ძიება სახელით, ტელეფონით, ელ. ფოსტით...",
  },
  "admin.inquiries.all_statuses": {"en": "All statuses", "ka": "ყველა სტატუსი"},
  "admin.inquiries.follow_up": {"en": "Follow-up", "ka": "შემდგომი"},
  "admin.inquiries.note": {"en": "Internal note", "ka": "შიდა შენიშვნა"},
  "admin.inquiries.note_ph": {"en": "Visible only to admins", "ka": "ჩანს მხოლოდ ადმინისთვის"},
  "admin.inquiries.message": {"en": "Message", "ka": "შეტყობინება"},
  "admin.inquiries.language": {"en": "Language", "ka": "ენა"},
  "admin.inquiries.notify": {"en": "Email notification", "ka": "ელ. ფოსტის შეტყობინება"},
  "admin.inquiries.not_sent": {"en": "Not sent", "ka": "არ გაიგზავნა"},
  "admin.inquiries.back": {"en": "Back", "ka": "უკან"},
}
