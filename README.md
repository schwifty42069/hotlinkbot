r/hlsvillage hotlinkbot
-------------------------


**Syntax**



Every statement of a bot summon comment ***must*** end with a semicolon. To summon the bot, begin your comment with the following:


```
!hotlinkbot;
```


Every bot summon comment ***must*** include a *media* identifier of either **tvod(TV on demand)**, **movie** or **live** and a *title* or *channel* (for live tv) identifier. For example:


```
!hotlinkbot; media=movie; title=El Camino;
```


If the *media* identifier you select is **live,** you ***must*** include a *channel* identifier, like the example below. It also ***must*** be from the following list (you don't have to type the quotes!):



**NOTE: LIVE TV LINKS ARE m3u8 FORMAT, WHICH MEANS THEY ARE PURE HLS AND WILL NOT WORK IN A BROWSER WITHOUT AN ADDON.**


*Most of the codes are obvious, but CN is not a typo, it is Cartoon Network*

```
'ABC', 'AE', 'AMC', 'Animal', 'BBCAmerica', 'BET', 'Boomerang', 'Bravo', 'CN', 'CBS',
'CMT', 'CNBC', 'CNN', 'Comedy', 'DA', 'Discovery', 'Disney', 'DisneyJr', 'DisneyXD',
'DIY', 'E', 'ESPN', 'ESPN2', 'FoodNetwork', 'FoxBusiness', 'FOX', 'FoxNews', 'FS1',
'FS2', 'Freeform', 'FX', 'FXMovie', 'FXX', 'GOLF', 'GSN', 'Hallmark', 'HMM', 'HBO',
'HGTV', 'History', 'HLN', 'ID', 'Lifetime', 'LifetimeM', 'MLB', 'MotorTrend', 'MSNBC',
'MTV', 'NatGEOWild', 'NatGEO', 'NBA', 'NBCSN', 'NBC', 'NFL', 'Nickelodeon',
'Nicktoons', 'OWN', 'Oxygen', 'Paramount', 'PBS', 'POP', 'Science', 'Showtime',
'StarZ', 'SundanceTV', 'SYFY', 'TBS', 'TCM', 'Telemundo', 'Tennis', 'CWE',
'TLC', 'TNT', 'Travel', 'TruTV', 'TVLand', 'Univision', 'USANetwork', 'VH1', 'WETV'
```

Live tv example:


```
!hotlinkbot; media=live; channel=HBO;
```


If the *media* identifier you select is **tvod,** you ***must*** also include a *season* and *episode* identifier. For example:


```
!hotlinkbot; media=tvod; title=Breaking Bad; season=4; episode=4;
```


If the *media* identifier you select is **movie,** then you need only to include the *summon keyword* and *title.* For example:


```
!hotlinkbot; media=movie; title=The Social Network;
```
