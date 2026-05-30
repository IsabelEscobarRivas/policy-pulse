SOURCES = [
    {
        "source_name": "Federal Register USCIS",
        "source_type": "federal_register",
        "base_url": "https://www.federalregister.gov/api/v1/documents.json?agencies[]=citizenship-and-immigration-services&order=newest&per_page=20",
        "retrieval_method": "api",
        "active": True,
    },
    {
        "source_name": "Federal Register USCIS Rules",
        "source_type": "federal_register_rules",
        "base_url": "https://www.federalregister.gov/api/v1/documents.json?agencies[]=citizenship-and-immigration-services&order=newest&per_page=20&type[]=Rule&type[]=Proposed%20Rule",
        "retrieval_method": "api",
        "active": True,
    },
    {
        "source_name": "Boundless Visa Bulletin",
        "source_type": "visa_bulletin",
        "base_url": "https://www.boundless.com/blog/visa-bulletin",
        "retrieval_method": "html",
        "active": True,
    },
]
