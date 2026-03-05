# WarEra API Documentation

This document provides detailed information about the WarEra tRPC API endpoints.
**Note:** Please be aware that although the openapi.json specifies POST for all calls, every call is in GET.

## Endpoints

### company

| Method                            | Endpoint              | Summary                       | Description                                                      |
| --------------------------------- | --------------------- | ----------------------------- | ---------------------------------------------------------------- |
| GET                               | /company.getById      | Get company by ID             | Retrieves detailed information about a specific company          |
| **Parameters**                    |
| `companyId`                       | string                | **Required**                  | The unique identifier of the company                             |
| **Response**                      |
| `result.data`                     | object                |                               | The company object                                               |
| `result.data._id`                 | string                |                               | The company unique identifier                                    |
| `result.data.name`                | string                |                               | The company name                                                 |
| `result.data.user`                | string                |                               | The ID of the user who owns the company                          |
| `result.data.region`              | string                |                               | The ID of the region where the company is located                |
| `result.data.itemCode`            | string                |                               | The code of the item the company produces                        |
| `result.data.production`          | number                |                               | The company production value                                     |
| `result.data.activeUpgradeLevels` | object                |                               | Levels of various upgrades (storage, automatedEngine, breakRoom) |
| `result.data.estimatedValue`      | number                |                               | Estimated value of the company                                   |
| GET                               | /company.getCompanies | Get companies with pagination | Retrieves a paginated list of companies with optional filtering  |
| **Parameters**                    |
| `userId`                          | string                | Optional                      | Filter companies by user ID                                      |
| `orgId`                           | string                | Optional                      | Filter companies by organization ID                              |
| `perPage`                         | number                | Optional                      | Number of companies per page (1-100), default: 10                |
| `cursor`                          | string                | Optional                      | Pagination cursor for next page                                  |
| **Response**                      |
| `result.data.items`               | array                 |                               | List of company IDs                                              |
| `result.data.nextCursor`          | string                |                               | Cursor for the next page of results                              |

### country

| Method                 | Endpoint                 | Summary           | Description                                             |
| ---------------------- | ------------------------ | ----------------- | ------------------------------------------------------- |
| GET                    | /country.getCountryById  | Get country by ID | Retrieves detailed information about a specific country |
| **Parameters**         |
| `countryId`            | string                   | **Required**      | The unique identifier of the country                    |
| **Response**           |
| `result.data`          | object                   |                   | The country object                                      |
| `result.data._id`      | string                   |                   | The country unique identifier                           |
| `result.data.name`     | string                   |                   | The country name                                        |
| `result.data.code`     | string                   |                   | The country ISO code                                    |
| `result.data.money`    | number                   |                   | The amount of money in the country treasury             |
| `result.data.taxes`    | object                   |                   | The country tax rates (income, market, selfWork)        |
| `result.data.allies`   | array                    |                   | List of IDs of allied countries                         |
| `result.data.warsWith` | array                    |                   | List of IDs of countries currently at war with          |
| `result.data.rankings` | object                   |                   | Country rankings in various categories                  |
| GET                    | /country.getAllCountries | Get all countries | Retrieves a list of all available countries             |
| **Response**           |
| `result.data`          | array                    |                   | List of all country objects                             |

### event

| Method                          | Endpoint                  | Summary              | Description                                                                       |
| ------------------------------- | ------------------------- | -------------------- | --------------------------------------------------------------------------------- |
| GET                             | /event.getEventsPaginated | Get paginated events | Retrieves a paginated list of events with optional country and event type filters |
| **Parameters**                  |
| `limit`                         | number                    | Optional             | The limit of events to get, default: 10                                           |
| `cursor`                        | string                    | Optional             | The cursor to get the next events                                                 |
| `countryId`                     | string                    | Optional             | Filter events by country ID                                                       |
| `eventTypes`                    | array                     | Optional             | Filter events by event types                                                      |
| **Response**                    |
| `result.data.items`             | array                     |                      | List of event objects                                                             |
| `result.data.items[]._id`       | string                    |                      | Event unique identifier                                                           |
| `result.data.items[].countries` | array                     |                      | IDs of countries involved in the event                                            |
| `result.data.items[].data`      | object                    |                      | Event details (type, IDs of related entities like battle, region)                 |
| `result.data.nextCursor`        | string                    |                      | Cursor for the next page of results                                               |

### government

| Method                        | Endpoint                   | Summary                      | Description                                             |
| ----------------------------- | -------------------------- | ---------------------------- | ------------------------------------------------------- |
| GET                           | /government.getByCountryId | Get government by country ID | Retrieves government information for a specific country |
| **Parameters**                |
| `countryId`                   | string                     | **Required**                 | The unique identifier of the country                    |
| **Response**                  |
| `result.data`                 | object                     |                              | The government object                                   |
| `result.data.president`       | string                     |                              | The ID of the country president                         |
| `result.data.vicePresident`   | string                     |                              | The ID of the country vice president                    |
| `result.data.congressMembers` | array                      |                              | List of IDs of congress members                         |

### region

| Method                          | Endpoint                 | Summary          | Description                                                       |
| ------------------------------- | ------------------------ | ---------------- | ----------------------------------------------------------------- |
| GET                             | /region.getById          | Get region by ID | Retrieves detailed information about a specific region            |
| **Parameters**                  |
| `regionId`                      | string                   | **Required**     | The unique identifier of the region                               |
| **Response**                    |
| `result.data`                   | object                   |                  | The region object                                                 |
| `result.data._id`               | string                   |                  | The region unique identifier                                      |
| `result.data.name`              | string                   |                  | The region name                                                   |
| `result.data.country`           | string                   |                  | The ID of the country that currently owns the region              |
| `result.data.isCapital`         | boolean                  |                  | Whether the region is the country's capital                       |
| `result.data.neighbors`         | array                    |                  | List of IDs of neighboring regions                                |
| `result.data.strategicResource` | string                   |                  | The strategic resource produced in the region                     |
| GET                             | /region.getRegionsObject | Get all regions  | Retrieves a complete object containing all available regions      |
| **Response**                    |
| `result.data`                   | object                   |                  | An object where keys are region IDs and values are region objects |

### battle

| Method                     | Endpoint                  | Summary              | Description                                                         |
| -------------------------- | ------------------------- | -------------------- | ------------------------------------------------------------------- |
| GET                        | /battle.getById           | Get battle by ID     | Retrieves detailed information about a specific battle              |
| **Parameters**             |
| `battleId`                 | string                    | **Required**         | The unique identifier of the battle                                 |
| **Response**               |
| `result.data`              | object                    |                      | The battle object                                                   |
| `result.data._id`          | string                    |                      | Battle unique identifier                                            |
| `result.data.attacker`     | object                    |                      | Attacker details (region, country, damages, hitCount)               |
| `result.data.defender`     | object                    |                      | Defender details (region, country, damages, hitCount)               |
| `result.data.isActive`     | boolean                   |                      | Whether the battle is currently active                              |
| `result.data.currentRound` | string                    |                      | The ID of the current round                                         |
| GET                        | /battle.getLiveBattleData | Get live battle data | Retrieves real-time battle data including current round information |
| **Parameters**             |
| `battleId`                 | string                    | **Required**         | The unique identifier of the battle                                 |
| `roundNumber`              | number                    | Optional             | Optional specific round number to retrieve                          |
| **Response**               |
| `result.data.battle`       | object                    |                      | Summary battle status and round IDs                                 |
| `result.data.round`        | object                    |                      | Current round live statistics (damages, points, next tick)          |
| GET                        | /battle.getBattles        | Get battles          | Retrieves a list of battles                                         |
| **Parameters**             |
| `isActive`                 | boolean                   | Optional             | Whether to get active battles                                       |
| `limit`                    | number                    | Optional             | The limit of battles to get, default: 10                            |
| `cursor`                   | string                    | Optional             | The cursor to get the next battles                                  |
| `direction`                | string                    | Optional             | The direction to get the battles (forward or backward)              |
| `filter`                   | string                    | Optional             | Filter type for battles (all, yourCountry, yourEnemies)             |
| `defenderRegionId`         | string                    | Optional             | Filter battles by defender region ID                                |
| `warId`                    | string                    | Optional             | Filter battles by war ID                                            |
| `countryId`                | string                    | Optional             | Filter battles by country ID                                        |
| **Response**               |
| `result.data.items`        | array                     |                      | List of battle objects with full details and current round stats    |
| `result.data.nextCursor`   | string                    |                      | Cursor for the next page of results                                 |

### round

| Method                 | Endpoint           | Summary                | Description                                                       |
| ---------------------- | ------------------ | ---------------------- | ----------------------------------------------------------------- |
| GET                    | /round.getById     | Get round by ID        | Retrieves detailed information about a specific battle round      |
| **Parameters**         |
| `roundId`              | string             | **Required**           | The unique identifier of the round                                |
| **Response**           |
| `result.data`          | object             |                        | The round object                                                  |
| `result.data.attacker` | object             |                        | Attacker round stats (damages, points, lastHits)                  |
| `result.data.defender` | object             |                        | Defender round stats (damages, points, lastHits)                  |
| `result.data.live`     | object             |                        | Live timing and tick info                                         |
| GET                    | /round.getLastHits | Get last hits in round | Retrieves the most recent hits/damages in a specific battle round |
| **Parameters**         |
| `roundId`              | string             | **Required**           | The unique identifier of the round                                |
| **Response**           |
| `result.data.attacker` | array              |                        | List of recent hits by the attacker                               |
| `result.data.defender` | array              |                        | List of recent hits by the defender                               |

### battleRanking

| Method                 | Endpoint                  | Summary             | Description                                                                                    |
| ---------------------- | ------------------------- | ------------------- | ---------------------------------------------------------------------------------------------- |
| GET                    | /battleRanking.getRanking | Get battle rankings | Retrieves damage, ground, or money rankings for users or countries in battles, rounds, or wars |
| **Parameters**         |
| `battleId`             | string                    | Optional            | Optional battle ID to filter rankings                                                          |
| `roundId`              | string                    | Optional            | Optional round ID to filter rankings                                                           |
| `warId`                | string                    | Optional            | Optional war ID to filter rankings                                                             |
| `dataType`             | string                    | **Required**        | Type of ranking data to retrieve (damage, points, or money)                                    |
| `type`                 | string                    | **Required**        | Whether to rank by user or country                                                             |
| `side`                 | string                    | **Required**        | Which side of the battle to rank (attacker or defender)                                        |
| **Response**           |
| `result.data.rankings` | array                     |                     | List of ranking entries (user ID, value, rank, lootChance)                                     |

### itemTrading

| Method        | Endpoint               | Summary         | Description                                                     |
| ------------- | ---------------------- | --------------- | --------------------------------------------------------------- |
| GET           | /itemTrading.getPrices | Get item prices | Retrieves current market prices for all tradeable items         |
| **Response**  |
| `result.data` | object                 |                 | Key-value pairs where keys are item codes and values are prices |

### tradingOrder

| Method                   | Endpoint                   | Summary                     | Description                             |
| ------------------------ | -------------------------- | --------------------------- | --------------------------------------- |
| GET                      | /tradingOrder.getTopOrders | Get best orders for an item | Retrieves the best orders for an item   |
| **Parameters**           |
| `itemCode`               | string                     | **Required**                | The item code to get orders for         |
| `limit`                  | integer                    | Optional                    | The limit of orders to get, default: 10 |
| **Response**             |
| `result.data.buyOrders`  | array                      |                             | List of top buy order objects           |
| `result.data.sellOrders` | array                      |                             | List of top sell order objects          |

### itemOffer

| Method         | Endpoint           | Summary              | Description                                                |
| -------------- | ------------------ | -------------------- | ---------------------------------------------------------- |
| GET            | /itemOffer.getById | Get item offer by ID | Retrieves detailed information about a specific item offer |
| **Parameters** |
| `itemOfferId`  | string             | **Required**         | The unique identifier of the item offer                    |
| **Response**   |
| `result.data`  | object             |                      | The item offer object (item, quantity, price, etc.)        |

### workOffer

| Method                   | Endpoint                           | Summary                      | Description                                                                       |
| ------------------------ | ---------------------------------- | ---------------------------- | --------------------------------------------------------------------------------- |
| GET                      | /workOffer.getById                 | Get work offer by ID         | Retrieves detailed information about a specific work offer                        |
| **Parameters**           |
| `workOfferId`            | string                             | **Required**                 | The unique identifier of the work offer                                           |
| **Response**             |
| `result.data`            | object                             |                              | The work offer object                                                             |
| GET                      | /workOffer.getWorkOfferByCompanyId | Get work offer by company ID | Retrieves work offer for a specific company                                       |
| **Parameters**           |
| `companyId`              | string                             | **Required**                 | The unique identifier of the company                                              |
| **Response**             |
| `result.data`            | object                             |                              | The work offer object associated with the company                                 |
| GET                      | /workOffer.getWorkOffersPaginated  | Get paginated work offers    | Retrieves a paginated list of work offers with optional user and region filtering |
| **Parameters**           |
| `userId`                 | string                             | Optional                     | The unique identifier of the user                                                 |
| `regionId`               | string                             | Optional                     | The unique identifier of the region                                               |
| `cursor`                 | string                             | Optional                     | The cursor to get the next work offers                                            |
| `limit`                  | integer                            | Optional                     | The limit of work offers to get, default: 10                                      |
| `energy`                 | number                             | Optional                     | The minimum energy required for the work offer                                    |
| `production`             | number                             | Optional                     | The minimum production required for the work offer                                |
| `citizenship`            | string                             | Optional                     | The citizenship required for the work offer                                       |
| **Response**             |
| `result.data.items`      | array                              |                              | List of work offer objects                                                        |
| `result.data.nextCursor` | string                             |                              | Cursor for the next page of results                                               |

### ranking

| Method              | Endpoint            | Summary          | Description                                                                         |
| ------------------- | ------------------- | ---------------- | ----------------------------------------------------------------------------------- |
| GET                 | /ranking.getRanking | Get ranking data | Retrieves ranking data for the specified ranking type and optional year-week filter |
| **Parameters**      |
| `rankingType`       | string              | **Required**     | The type of ranking to retrieve                                                     |
| **Response**        |
| `result.data`       | object              |                  | The ranking container object                                                        |
| `result.data.type`  | string              |                  | The ranking category type                                                           |
| `result.data.items` | array               |                  | List of ranking entries (entity ID, value, rank, tier)                              |

### search

| Method         | Endpoint               | Summary       | Description                                                                    |
| -------------- | ---------------------- | ------------- | ------------------------------------------------------------------------------ |
| GET            | /search.searchAnything | Global search | Performs a global search across users, companies, articles, and other entities |
| **Parameters** |
| `searchText`   | string                 | **Required**  | The search query string                                                        |
| **Response**   |
| `result.data`  | object                 |               | Lists of matching IDs for various categories (userIds, muIds, etc.)            |

### gameConfig

| Method        | Endpoint                  | Summary                | Description                                                                          |
| ------------- | ------------------------- | ---------------------- | ------------------------------------------------------------------------------------ |
| GET           | /gameConfig.getDates      | Get game dates         | Retrieves game-related dates and timings                                             |
| **Response**  |
| `result.data` | object                    |                        | Object containing various game events and regen timestamps                           |
| GET           | /gameConfig.getGameConfig | Get game configuration | Retrieves static game configuration                                                  |
| **Response**  |
| `result.data` | object                    |                        | Massive configuration object containing skill info, item data, upgrade details, etc. |

### user

| Method              | Endpoint                | Summary                 | Description                                                                              |
| ------------------- | ----------------------- | ----------------------- | ---------------------------------------------------------------------------------------- |
| GET                 | /user.getUserLite       | Get user profile (lite) | Retrieves basic public information about a user including username, skills, and rankings |
| **Parameters**      |
| `userId`            | string                  | **Required**            | The unique identifier of the user                                                        |
| **Response**        |
| `result.data`       | object                  |                         | User profile object containing username, level, skills, and stats                        |
| GET                 | /user.getUsersByCountry | Get users by country    | Retrieves a list of users by country                                                     |
| **Parameters**      |
| `countryId`         | string                  | **Required**            | The unique identifier of the country                                                     |
| `limit`             | number                  | Optional                | The limit of users to get, default: 10                                                   |
| `cursor`            | string                  | Optional                | The cursor to get the next users                                                         |
| **Response**        |
| `result.data.items` | array                   |                         | List of user summary objects (ID and creation date)                                      |

### article

| Method                   | Endpoint                      | Summary                | Description                                               |
| ------------------------ | ----------------------------- | ---------------------- | --------------------------------------------------------- |
| GET                      | /article.getArticleById       | Get article by ID      | Retrieves detailed information about a specific article   |
| **Parameters**           |
| `articleId`              | string                        | **Required**           | The ID of the article to get                              |
| **Response**             |
| `result.data`            | object                        |                        | The article object with title, content, author, and stats |
| GET                      | /article.getArticlesPaginated | Get paginated articles | Retrieves a paginated list of articles                    |
| **Parameters**           |
| `type`                   | string                        | **Required**           | The type of articles to get                               |
| `limit`                  | number                        | Optional               | The limit of articles to get, default: 10                 |
| `cursor`                 | string                        | Optional               | The cursor to get the next articles                       |
| `userId`                 | string                        | Optional               | The user ID to get articles for                           |
| `categories`             | array                         | Optional               | The categories to get articles for                        |
| `languages`              | array                         | Optional               | The languages to get articles for                         |
| **Response**             |
| `result.data.items`      | array                         |                        | List of article objects                                   |
| `result.data.nextCursor` | string                        |                        | Cursor for the next page of results                       |

### mu

| Method                   | Endpoint             | Summary                        | Description                                                        |
| ------------------------ | -------------------- | ------------------------------ | ------------------------------------------------------------------ |
| GET                      | /mu.getById          | Get military unit by ID        | Retrieves detailed information about a specific military unit      |
| **Parameters**           |
| `muId`                   | string               | **Required**                   | The unique identifier of the military unit                         |
| **Response**             |
| `result.data`            | object               |                                | The MU object (name, members, roles, rankings)                     |
| GET                      | /mu.getManyPaginated | Get military units (paginated) | Retrieves a paginated list of military units with optional filters |
| **Parameters**           |
| `limit`                  | number               | Optional                       | The limit of military units to get, default: 20                    |
| `cursor`                 | string               | Optional                       | The cursor to get the next military units                          |
| `memberId`               | string               | Optional                       | The member ID to get military units for                            |
| `userId`                 | string               | Optional                       | The user ID to get military units for                              |
| `orgId`                  | string               | Optional                       | The organization ID to get military units for                      |
| `search`                 | string               | Optional                       | The search query to filter military units                          |
| **Response**             |
| `result.data.items`      | array                |                                | List of MU objects                                                 |
| `result.data.nextCursor` | string               |                                | Cursor for the next page of results                                |

### transaction

| Method                   | Endpoint                              | Summary                    | Description                                                       |
| ------------------------ | ------------------------------------- | -------------------------- | ----------------------------------------------------------------- |
| GET                      | /transaction.getPaginatedTransactions | Get paginated transactions | Retrieves a paginated list of transactions                        |
| **Parameters**           |
| `limit`                  | integer                               | Optional                   | The limit of transactions to get, default: 10                     |
| `cursor`                 | string                                | Optional                   | The cursor to get the next transactions                           |
| `userId`                 | string                                | Optional                   | The user ID to get transactions for                               |
| `muId`                   | string                                | Optional                   | The MU ID to get transactions for                                 |
| `countryId`              | string                                | Optional                   | The country ID to get transactions for                            |
| `itemCode`               | string                                | Optional                   | The item code to get transactions for                             |
| `transactionType`        | anyOf                                 | Optional                   | The type of transactions to get                                   |
| **Response**             |
| `result.data.items`      | array                                 |                            | List of transaction objects (money, quantity, type, participants) |
| `result.data.nextCursor` | string                                |                            | Cursor for the next page of results                               |

### upgrade

| Method         | Endpoint                           | Summary                        | Description                                                                                              |
| -------------- | ---------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| GET            | /upgrade.getUpgradeByTypeAndEntity | Get upgrade by type and entity | Retrieves upgrade information for a specific upgrade type and entity (region, company, or military unit) |
| **Parameters** |
| `upgradeType`  | string                             | **Required**                   | The upgrade type to get                                                                                  |
| `regionId`     | string                             | Optional                       | The region ID to get upgrade for                                                                         |
| `companyId`    | string                             | Optional                       | The company ID to get upgrade for                                                                        |
| `muId`         | string                             | Optional                       | The military unit ID to get upgrade for                                                                  |
| **Response**   |
| `result.data`  | object                             |                                | The upgrade configuration object for the specified entity type and level                                 |
