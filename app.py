#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
import datetime
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import *
from flask_migrate import Migrate
import sys
from sqlalchemy.exc import SQLAlchemyError

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Helpers
#----------------------------------------------------------------------------#
def get_or_create_genres(genre_names):
    """
    Accepts an iterable of genre names (strings).
    Returns a list of Genre objects (existing or newly created).
    """
    genres_objs = []
    for g in genre_names:
        name = g.strip()
        if not name:
            continue
        genre = Genre.query.filter_by(name=name).first()
        if not genre:
            genre = Genre(name=name)
            db.session.add(genre)
            db.session.flush()
            # We don't commit here; commit will be performed by caller
        genres_objs.append(genre)
    return genres_objs
#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO: replace with real venues data.
  #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue.
    today=datetime.today()
    data = []
    prev=[]
    prevCity_State=''
    try:
        venues = Venue.query.order_by(Venue.state, Venue.city).all()
        for venue in venues:
            upComingShows = Show.query.filter(Show.venue_id == venue.id, Show.start_time > today).all()
            venue_data={
              "id":venue.id,
              "name":venue.name,
              "numUpComingShows":len(upComingShows)}
            if len(data) > 0:
              prev=data[len(data) - 1]
              prevCity_State =  prev['city']+ prev['state']
              if prevCity_State == venue.city + venue.state:
                prev['venues'].append(venue_data)
                continue
            data.append({
              'city': venue.city,
              'state': venue.state,
              'venues': [venue_data]})
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error("Unexpected error: %s", e, exc_info=True)
        flash("Oops! Something went wrong. Please try again.")
        return render_template("pages/home.html")

    finally:
        return render_template("pages/venues.html", areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    response = {"count": 0, "data": []}
    search_term = request.form.get("search_term", "").strip()
    try:
        
        results = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()
        for result in results:
          num_upcoming = db.session.query(Show).filter(Show.venue_id == result.id, Show.start_time > datetime.utcnow()).count()
          item = {
            "id": result.id,
            "name": result.name,
            "num_upcoming_shows": num_upcoming
            }
          response["data"].append(item)
        response["count"] = len(results)
    except Exception as e:
        app.logger.error("Venue search failed for term '%s': %s", search_term, e, exc_info=True)
        flash('An error occurred for the search term' +
              request.form.get('search_term', ''))
    finally:
        return render_template('pages/search_venues.html', results=response,search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    """Show venue details, with past and upcoming shows."""
    data = {}
    try:
        venue = Venue.query.get(venue_id)
        if not venue:
            flash("This venue does not exist.")
            return render_template("errors/404.html")

        # genres: venue.genres is a list of Genre objects; use .name
        genres = [g.name for g in venue.genres]

        today = datetime.utcnow()
        raw_upcoming_shows = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id, Show.start_time > today).all()
        upcoming_shows = [{
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.start_time)
        } for show in raw_upcoming_shows]

        raw_past_shows = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id, Show.start_time <= today).all()
        past_shows = [{
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.start_time)
        } for show in raw_past_shows]

        data = {
            "id": venue.id,
            "name": venue.name,
            "city": venue.city,
            "state": venue.state,
            "address": venue.address,
            "genres": genres,
            "phone": venue.phone,
            "website": venue.website,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
            "upcoming_shows_count": len(upcoming_shows),
            "upcoming_shows": upcoming_shows,
            "past_shows_count": len(past_shows),
            "past_shows": past_shows,
        }
    except SQLAlchemyError as e:
        app.logger.error("Failed to fetch venue %s: %s", venue_id, e, exc_info=True)
        flash("Oops! Something went wrong. Please try again.")
    finally:
        db.session.close()

    return render_template("pages/show_venue.html", venue=data)
#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        form = VenueForm(request.form)
        genres_list = request.form.getlist('genres')  # list of strings
        venue = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            phone=form.phone.data,
            address=form.address.data,
            image_link=form.image_link.data,
            website=form.website_link.data,
            facebook_link=form.facebook_link.data,
            seeking_talent=form.seeking_talent.data,
            seeking_description=form.seeking_description.data
        )
        # associate Genre objects
        venue.genres = get_or_create_genres(genres_list)
        db.session.add(venue)
        db.session.commit()
        flash("Venue " + venue.name + " has been successfully listed!")
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error("Failed to create venue: %s", e, exc_info=True)
        flash("An error occurred. Venue " + request.form.get("name", "") + " could not be listed.")
    finally:
        db.session.close()

    return render_template('pages/home.html')
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success
  #flash('Venue ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  #return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue = Venue.query.get(venue_id)
    if not venue:
            flash("Venue not found.")
    venue.delete()
    flash("Venue: " + venue.name + " was successfully deleted.")
  except SQLAlchemyError as e:
    db.session.rollback()
    app.logger.error("Unexpected error: %s", e, exc_info=True)
    flash("Venue: " + venue.name + " could not be deleted.")
  finally:
    db.session.close()
  return render_template("pages/home.html")
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database
  
  return render_template('pages/artists.html', artists=Artist.query.all())

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term','')
  search_results = Artist.query.filter(Artist.name.ilike('%{}%'.format(search_term))).all()
  search_response = {"count": len(search_results), "data": []}
  for result in search_results:
    num_upcoming = db.session.query(Show).filter(Show.artist_id == result.id, Show.start_time > datetime.utcnow()).count()
    artist={
      "id":result.id,
      "name":result.name,
      "num_upcoming_shows": num_upcoming,}
    search_response["data"].append(artist)
  return render_template('pages/search_artists.html', results=search_response, search_term=request.form.get('search_term', ''))
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
 

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = {}
    try:
        requested_artist = Artist.query.get(artist_id)
        if requested_artist is None:
            flash("This artist does not exist.")
            return not_found_error(404)

        genres = [g.name for g in requested_artist.genres]

        today = datetime.utcnow()
        shows_q = Show.query.filter(Show.artist_id == artist_id)
        past = shows_q.filter(Show.start_time < today).all()
        upcoming = shows_q.filter(Show.start_time >= today).all()

        past_shows = []
        for show in past:
            venue = Venue.query.get(show.venue_id)
            past_shows.append({
                "venue_id": venue.id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
                "start_time": str(show.start_time)
            })

        upcoming_shows = []
        for show in upcoming:
            venue = Venue.query.get(show.venue_id)
            upcoming_shows.append({
                "venue_id": venue.id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
                "start_time": str(show.start_time)
            })

        data = {
            "id": requested_artist.id,
            "name": requested_artist.name,
            "genres": genres,
            "city": requested_artist.city,
            "state": requested_artist.state,
            "phone": requested_artist.phone,
            "seeking_venue": requested_artist.seeking_venue,
            "facebook_link": requested_artist.facebook_link,
            "image_link": requested_artist.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": len(past_shows),
            "upcoming_shows_count": len(upcoming_shows),
        }
    except SQLAlchemyError as e:
        app.logger.error("Failed to fetch artist %s: %s", artist_id, e, exc_info=True)
        flash("Oops! Something went wrong. Please try again.")
    finally:
        db.session.close()

    return render_template("pages/show_artist.html", artist=data)



  # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artist table, using artist_id
  
#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  try:
    requested_artist = Artist.query.get(artist_id)
    if requested_artist is None:
      return not_found_error(404)
    form = ArtistForm(
      name=requested_artist.name,
      genres = [g.name for g in requested_artist.genres],
      city=requested_artist.city,
      state=requested_artist.state,
      phone=requested_artist.phone,
      website=requested_artist.website,
      facebook_link=requested_artist.facebook_link,
      seeking_venue=requested_artist.seeking_venue,
      seeking_description=requested_artist.seeking_description,
      image_link=requested_artist.image_link)

  except Exception as e:
        app.logger.error("Error preparing edit artist form: %s", e, exc_info=True)
        flash("Oops! Something went wrong. Please try again.")
        return redirect(url_for("index"))
  finally:
    db.session.close()
  return render_template('forms/edit_artist.html', form=form, artist=requested_artist)
  # TODO: populate form with fields from artist with ID <artist_id>
  

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  
  error=False
  try:
    form = ArtistForm(request.form)
    artist = Artist.query.get(artist_id)

    if artist is None:
      return not_found_error(404) 
    genres = request.form.getlist("genres") 

    artist.name = request.form.get("name")
    artist.city = request.form.get("city")
    artist.state = request.form.get("state")
    artist.phone = request.form.get("phone")
    artist.facebook_link = request.form.get("facebook_link")
    artist.image_link = request.form.get("image_link")
    artist.genres = get_or_create_genres(genres)
    db.session.add(artist)
    db.session.commit()

    db.session.refresh(artist)
    flash('Artist ' + request.form.get("name") + ' was successfully updated!')

  except SQLAlchemyError as e:
    error = True
    db.session.rollback()
    app.logger.error("Failed to update artist %s: %s", artist_id, e, exc_info=True)
    flash("An error occurred. Artist " + request.form.get("name", "") + " could not be updated.")
  finally:
    db.session.close()
    if error:
      return render_template('forms/edit_artist.html', form=form, artist=artist)
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  try:
    venue = Venue.query.get(venue_id)
    if venue is None:
      return not_found_error(404)
    form.name.data = venue.name
    form.city.data = venue.city
    form.state.data = venue.state
    form.address.data = venue.address
    form.phone.data = venue.phone
    form.genres.data = [g.name for g in venue.genres]
    form.facebook_link.data = venue.facebook_link
    form.image_link.data = venue.image_link
    form.website.data = venue.website
    form.seeking_talent.data = venue.seeking_talent
    form.seeking_description.data = venue.seeking_description
  except Exception as e:
    app.logger.error("Error preparing edit venue form: %s", e, exc_info=True)
    flash("Oops! Something went wrong. Please try again.")
    return redirect(url_for("index"))

  finally:
    db.session.close()
  return render_template('forms/edit_venue.html', form=form, venue=venue)

    
 
  # TODO: populate form with values from venue with ID <venue_id>


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:

    venue = Venue.query.get(venue_id)
    if venue is None:
      return not_found_error(404)
        
    venue.name = request.form.get("name")
    venue.city = request.form.get("city")
    venue.state = request.form.get("state")
    venue.address = request.form.get("address")
    venue.phone = request.form.get("phone")
    genresList = request.form.getlist("genres")
    venue.genres = get_or_create_genres(genresList)
    venue.facebook_link = request.form.get("facebook_link")
    db.session.add(venue)
    db.session.commit()
    db.session.refresh(venue)
    flash("This venue was successfully updated!")

  except SQLAlchemyError as e:
    db.session.rollback()
    app.logger.error("Unexpected error: %s", e, exc_info=True)
    flash("Oops! An error occurred. Venue "+ request.form.get("name")+ " could not be updated.")

  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    genresList = request.form.getlist("genres")
    newArtist = Artist(
      name=request.form.get("name"),
      city=request.form.get("city"),
      state=request.form.get("state"),
      phone=request.form.get("phone"),
      facebook_link=request.form.get("facebook_link"),
      image_link=request.form.get("image_link"),
      website=request.form.get("website"),
      seeking_venue=request.form.get("seeking_venue"),
      seeking_description=request.form.get("seeking_description"))
    newArtist.genres = get_or_create_genres(genresList)
    newArtist.add()
    db.session.refresh(newArtist)
        # on successful db insert, flash success
    flash("Artist: " + newArtist.name + " has been successfully listed!")
  except SQLAlchemyError as e:
    db.session.rollback()
    app.logger.error("Failed to create artist: %s", e, exc_info=True)
        # Done: on unsuccessful db insert, flash an error instead.
    flash("An error occurred. Artist could not be listed.")
  finally:
    db.session.close()
  return render_template("pages/home.html")

  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success
  #flash('Artist ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
  #return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  try:
    shows = Show.query.all()
    if shows is None:
      return not_found_error(404)
    for show in shows:
      data.append({
        'venue_id': show.venue.id,
        'venue_name': show.venue.name,
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': str(show.start_time)})

  except SQLAlchemyError as e:
    db.session.rollback()
    app.logger.error("Failed to fetch shows: %s", e, exc_info=True)
    flash("Oops! Something went wrong, please try again.")

  finally:
    return render_template("pages/shows.html", shows=data)
  # displays list of shows at /shows
  # TODO: replace with real venues data.
 
@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    form = ShowForm()
        #check if the artist exists in the database
    found_artist = Artist.query.get(form.artist_id.data)
    if found_artist is None:
      flash("There is no artist with id "+ request.form.get("artist_id")+ " in our records")
      raise Exception('artist not found')
    else:
             #check if the venue exists in the database
      found_venue = Venue.query.get(form.venue_id.data)
      if found_venue is None:
        flash("There is no venue with id "+ request.form.get("venue_id")+ " in our records")
        raise Exception('venue not found')
                
      else:
        show = Show(
          artist_id=form.artist_id.data,
          venue_id=form.venue_id.data,
          start_time=form.start_time.data,)
    show.add()
    flash("Show has been successfully listed!")

  except Exception as e:
    app.logger.error("Failed to create show: %s", e, exc_info=True)
    db.session.rollback()
    flash("Something went wrong and the show was not created. Please try again.")

  finally:
    db.session.close()

  return render_template('pages/home.html')
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead

  # on successful db insert, flash success
  #flash('Show was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  #return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    import os 
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
