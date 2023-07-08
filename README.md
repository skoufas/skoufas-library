# Skoufas Library

## Columns required

### BookEntry

- Title - Τίτλος
- Subtitle - Υπότιτλος
- SkoufasClassification - Ταξινομικός Αριθμός
- Edition - Έκδοση
- EditionDate - Έτος Έκδοσης
- EditorId (FK: Editor)
- Pages - Σελίδες Αριθμητικά
- Volumes - Τόμοι/Τεύχη
- Notes - Σημειώσεις
- Material - Υλικό
- HasCD - Έχει
- HasDVD - Έχει
- ISBN
- ISSN
- EAN
- Offprint - ΑΝΑΤΥΠΟ

### Author - Συγγραφέας

- Name
- Surname
- Middlename
- Fullname

### Authorship (Many-to-Many)

- AuthorId (FK: Author)
- BookEntryId (FK: BookEntry)

### Translator - Μεταφραστής

- Name
- Surname
- Middlename
- Fullname

### Translation

- TranslatorId (FK: Translator)
- BookEntryId (FK: BookEntry)

### Curator - Επιμελητής

- Name
- Surname
- Middlename
- Fullname

### Curation

- CuratorId (FK: Curator)
- BookEntryId (FK: BookEntry)

### Editor

- Name
- Place

### Entry Numbers (one-to-many) - Αριθμοί Εισαγωγής

- EntryNumber (unique)
- BookEntryId (FK: BookEntry)
- Copies

### Topic - Θέμα

- Name

### BookInTopic (many-to-many)

- TopicId (FK: Topic)
- BookEntryId (FK: BookEntry)

### Donor - Δωρητής

- Name
- Surname
- Middlename
- Fullname

### Donation (Many-to-Many) - Δωρεά

- DonorId (FK: Donor)
- EntryNumberId (FK: EntryNumber)

### Customer - Πελάτες

- Name
- Surname
- Middlename
- FullName
- IdNumber
- IdType
- PhoneNumber
- Email
- Address

### Loan - Δανεισμός

- CustomerId (FK: Customer)
- EntryNumberId (FK: EntryNumber)
- StartDateTime
- ExpectedEndDateTime
- EndDateTime
- Note
