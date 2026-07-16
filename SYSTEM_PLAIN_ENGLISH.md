# What This System Actually Is (in plain English)

*A no-jargon explanation of the software running The Glizzness — a one-cart hot-dog business in
Columbia, Missouri. Written to be handed to someone who is not technical.*

---

## The short version

A small food business had the same problems every small business has:

- **They kept missing opportunities.** Events, festivals, and shows were happening all over town and
  nobody had time to hunt for them.
- **Customers couldn't find them.** The cart moves. "Where are you today?" was a constant question.
- **The books were a chore.** Sales in one system, accounting in another, hours of retyping.
- **Everything lived in one person's head** — or worse, scattered across a phone, a notebook, and
  Facebook.

So we built them their own software. Not a subscription. Not an app off a shelf. Theirs.

**It costs about $0/month to run.** More on that below, because it's the part people don't believe.

---

## What it does, piece by piece

### 1. A robot that hunts for work
Every four hours, day and night, it checks about ten local sources — the university events calendar,
music venues, the local news, Reddit, brewery calendars — looking for anything happening nearby that a
food cart could sell at. It never forgets, never sleeps, never gets busy.

Whatever it finds lands in a private feed the owner skims like an inbox: **keep** or **dismiss**.
Dismissed things never come back. On its first run it found **178 real events.**

> **Being honest about this:** it is not magic and it does not "read the whole internet." Nobody's
> software does. It's a tireless assistant checking a curated list of places on a timer. The power isn't
> reach — it's that it *never forgets to look*, and the list grows over time.

### 2. A deck of cards for the guy who actually runs the cart
The owner-operator reads better through clear visual layout than through dense text. That's not a
footnote — it shaped the whole design.

So the opportunities he sees aren't a spreadsheet. They're **one big card at a time** on his phone:
how far, how long the drive, what it costs, how big the crowd, how many people he'd need. Three huge
buttons: **Yes / Maybe / No.** Plus one field to ask a question.

His answers land on his partner's desk. His partner does the research and books the winners.

**Nobody has to do the part of the job they're bad at.** That's the whole point.

### 3. A schedule that updates itself
The owner keeps his stops in a normal Google Calendar — same as always, nothing new to learn.

The website reads it automatically and shows customers where the cart will be. Every two hours it
refreshes itself, whether anyone's computer is on or not.

**The privacy detail that matters:** most gigs are private catering jobs — the client's name and address
are nobody's business. So a stop is only shown publicly if it's explicitly marked public. Everything else
appears as *"Booked — Unavailable."* Forget to mark something and it stays private. It can't leak by
accident, only by deliberate choice.

### 4. A public map of events
A map of hundreds of Midwest festivals, fairs, and events — filterable by month, distance, county, and
type. It started as an internal tool and became something genuinely useful to other people.

### 5. A website that's a real front door
Menu, ordering, catering booking, and the live schedule. When someone books catering, the owner gets an
email within seconds — no form sitting in a database unread.

The menu has a single source of truth: change it in one place, and the website *and* the point-of-sale
*and* the delivery app all update. No more three-places-to-forget.

### 6. Books that mostly do themselves
Sales flow from the payment system into the accounting software, categorized correctly, with the fiddly
edge cases (processing fees, discounts, tips, loan payments, tax rates) handled by rules instead of by
someone remembering at 11pm.

---

## The part people don't believe: what it costs

**Roughly zero dollars a month.**

Every piece runs on a free tier that's genuinely free at this scale — the website host, the database,
the scheduled robots, the dashboard. The only real bill is the domain name, about **$20 a year**.

Compare that to renting the same capabilities:

| What it replaces | Typical monthly cost |
|---|---|
| Website + hosting | $30–100 |
| Booking / lead capture tool | $30–80 |
| Event-finding service | $50–200 |
| Scheduling / dispatch tool | $40–100 |
| Bookkeeping automation | $30–80 |
| **Total** | **~$180–560/month** |

And that rented stack still wouldn't fit the business — it'd be five products that don't talk to each
other, none of which know that this particular operator reads better with pictures.

---

## Why build instead of buy

**You own it.** Not renting. The prices can't go up. It can't get discontinued, acquired, or
"sunset." Nobody changes the terms on you.

**Your data is yours.** It sits in your database, in your account, exportable any time.

**It fits how you actually work.** Off-the-shelf software makes you bend to its assumptions. This bent
to theirs: the calendar they already used, the way the operator reads, the fact that one partner hates
talking to people and the other hates paperwork.

**It compounds.** Every piece feeds the next. The calendar feeds the website. The finder feeds the card
board. The sales history will soon tell them how many people to staff — because it's all one system, not
five products with five logins.

---

## What it is *not*

Being straight, because the wrong client is worse than no client:

- **It's not a product you can buy.** It's built, per business. It's closer to hiring a contractor than
  buying a tool.
- **It needs a technical person** to build and occasionally maintain it. Free tiers aren't free of
  effort.
- **It's not instant.** This one took real work — including a full security audit and fixing everything
  that audit found, *before* anyone logged in.
- **It won't fix a broken business.** It removes friction and finds opportunities. It doesn't sell hot
  dogs for you.

---

## What it took

A working version of all of the above — crawler, private hub, card board, self-updating schedule,
website, accounting automation — plus documentation deep enough to rebuild the entire thing from
scratch if every account were deleted tomorrow.

The security wasn't assumed, it was **tested**: an independent audit found 14 issues, and every critical
one was fixed *before* the first login. The private data was then verified as genuinely unreachable from
the public internet — not "should be fine," but checked.

---

## Could this work for a business that isn't hot dogs?

Yes — the hot dogs are incidental. Underneath, the pattern is:

> *Find opportunities automatically → let a human make the call in ten seconds → keep a public face
> honest and current → let the boring parts run themselves.*

That shape fits a **landscaper**, a **food truck**, a **band**, a **mobile detailer**, a **wedding
photographer**, a **contractor**, a **market vendor** — anyone who moves around, chases opportunities,
and is too busy doing the work to also run software.

The pieces get swapped: different sources to watch, different card, different books. The skeleton is
the same. There's a full playbook for rebuilding it for someone else (`REPLICATION_PLAYBOOK.md`).

---

*Questions welcome — including the skeptical ones. The "$0/month" claim in particular deserves them,
and it holds up.*
