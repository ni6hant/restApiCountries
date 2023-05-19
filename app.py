import requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://flaskbloguser:WKNXpBOtYpcvtWBOpjMPFOAe1IgGuWWm@dpg-chgr2367avjbbjpntevg-a.oregon-postgres.render.com/flaskblogdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'WKNXpBOtYpcvtWBOpjMPFOAe1IgGuWWm'
db = SQLAlchemy(app)

# Country Model
class Country(db.Model):
    __tablename__ = 'country'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    cca3 = db.Column(db.String)
    currency_code = db.Column(db.String)
    currency = db.Column(db.String)
    capital = db.Column(db.String)
    region = db.Column(db.String)
    subregion = db.Column(db.String)
    area = db.Column(db.BigInteger)
    map_url = db.Column(db.String)
    population = db.Column(db.BigInteger)
    flag_url = db.Column(db.String)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    neighbours = db.relationship('CountryNeighbours', backref='country', foreign_keys='CountryNeighbours.country_id')

class CountryNeighbours(db.Model):
    __tablename__ = 'country_neighbours'
    id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    neighbour_country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

# Create Database if it doesn't exist
with app.app_context():
    db.create_all()

# API endpoint to populate countries
@app.route('/populate_countries', methods=['POST'])
def populate_countries():
    response = requests.get('https://restcountries.com/v3.1/all')
    data = response.json()

    for item in data:
        # Extract data from the item
        name = item['name']['common']
        cca3 = item['cca3']
        currencies = item.get('currencies', {})
        currency_data = next(iter(currencies.values()), {})
        currency_code = list(currencies)[0] if currencies else None
        currency = currency_data.get('name')
        capital = item.get('capital', [''])[0]
        region = item.get('region')
        subregion = item.get('subregion')
        area = item['area']
        map_url = item.get('maps', {}).get('googleMaps')
        population = item.get('population')
        flag_url = item['flags']['png']
        created_at = datetime.now()
        updated_at = datetime.now()

        # Create a new Country instance
        country = Country(
            name=name,
            cca3=cca3,
            currency_code=currency_code,
            currency=currency,
            capital=capital,
            region=region,
            subregion=subregion,
            area=area,
            map_url=map_url,
            population=population,
            flag_url=flag_url,
            created_at=created_at,
            updated_at=updated_at
        )

        # Add the country to the database session
        db.session.add(country)
        db.session.flush()  # Flush changes to get the auto-generated ID

        # Create country neighbors
        borders = item.get('borders', [])
        for neighbour_cca in borders:
            neighbour_country = Country.query.filter_by(cca3=neighbour_cca).first()
            if neighbour_country:
                country_neighbour = CountryNeighbours(
                    country_id=country.id,
                    neighbour_country_id=neighbour_country.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(country_neighbour)

    # Commit the changes to the database
    db.session.commit()

    return 'Countries populated successfully!'

# API to return all the countries
@app.route('/country', methods=['GET'])
def get_all_countries():
    sort_by = request.args.get('sort_by', 'a_to_z')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    name = request.args.get('name')
    region = request.args.get('region')
    subregion = request.args.get('subregion')

    query = Country.query

    if name:
        query = query.filter(Country.name.ilike(f'%{name}%'))
    if region:
        query = query.filter(Country.region.ilike(f'%{region}%'))
    if subregion:
        query = query.filter(Country.subregion.ilike(f'%{subregion}%'))

    total_count = query.count()
    total_pages = (total_count - 1) // limit + 1

    if sort_by == 'a_to_z':
        query = query.order_by(Country.name.asc())
    elif sort_by == 'z_to_a':
        query = query.order_by(Country.name.desc())
    elif sort_by == 'population_high_to_low':
        query = query.order_by(Country.population.desc())
    elif sort_by == 'population_low_to_high':
        query = query.order_by(Country.population.asc())
    elif sort_by == 'area_high_to_low':
        query = query.order_by(Country.area.desc())
    elif sort_by == 'area_low_to_high':
        query = query.order_by(Country.area.asc())

    paginated_query = query.paginate(page=page, per_page=limit)

    countries = []
    for country in paginated_query.items:
        countries.append({
            'id': country.id,
            'name': country.name,
            'cca3': country.cca3,
            'currency_code': country.currency_code,
            'currency': country.currency,
            'capital': country.capital,
            'region': country.region,
            'subregion': country.subregion,
            'area': country.area,
            'map_url': country.map_url,
            'population': country.population,
            'flag_url': country.flag_url,
        })

    response = {
        'countries': countries,
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'limit': limit
    }

    return jsonify(response)

# API to get a country detail
@app.route('/country/<int:country_id>', methods=['GET'])
def get_country_detail(country_id):
    country = Country.query.get(country_id)

    if country is None:
        return jsonify({
            'message': 'Country not found',
            'data': {}
        }), 404

    response = {
        'message': 'Country detail',
        'data': {
            'country': {
                'id': country.id,
                'name': country.name,
                'cca3': country.cca3,
                'currency_code': country.currency_code,
                'currency': country.currency,
                'capital': country.capital,
                'region': country.region,
                'subregion': country.subregion,
                'area': country.area,
                'map_url': country.map_url,
                'population': country.population,
                'flag_url': country.flag_url
            }
        }
    }

    return jsonify(response)

# API to get country neighbors
@app.route('/country/<int:country_id>/neighbour', methods=['GET'])
def get_country_neighbours(country_id):
    country = Country.query.get(country_id)

    if country is None:
        return jsonify({
            'message': 'Country not found',
            'data': {}
        }), 404

    neighbours = Country.query.join(CountryNeighbours, Country.id == CountryNeighbours.neighbour_country_id).filter(
        CountryNeighbours.country_id == country.id).all()

    country_neighbours = []
    for neighbour in neighbours:
        country_neighbours.append({
            'id': neighbour.id,
            'name': neighbour.name,
            'cca3': neighbour.cca3,
            'currency_code': neighbour.currency_code,
            'currency': neighbour.currency,
            'capital': neighbour.capital,
            'region': neighbour.region,
            'subregion': neighbour.subregion,
            'area': neighbour.area,
            'map_url': neighbour.map_url,
            'population': neighbour.population,
            'flag_url': neighbour.flag_url,
        })

    response = {
        'message': 'Country neighbours',
        'data': {
            'countries': country_neighbours
        }
    }

    return jsonify(response)


if __name__ == '__main__':
    app.run()
