Camping.goes :GtfsUpload

$workers = []

module GtfsUpload::Controllers
  class List < R('/')
    def get
      for worker in $workers
        if worker.status == 'done'
          worker.join
        end
      end
      render :tasklist
    end
  end

  class Upload < R('/upload')
    def post
      worker =  GtfsUpload::Helpers::Worker.new(@input['url'],
                                                @input['agencyname'],
                                                @input['city'])
      $workers << worker
      worker.fetch
      redirect List
    end
  end
end

module GtfsUpload::Views
  def layout
    html do
      head do
        title 'GTFS uploader'
      end
      body do
        self << yield
      end
    end
  end

  def tasklist
    if $workers.length > 0
      h3 "Currently processing"
      table do
        thead do
          th "Status"
          th "City"
          th "Agency"
          th "Filename"
          th "URL"
        end
        for worker in $workers
          tr do
            td worker.status.to_s
            td worker.city
            td worker.agencyname
            td worker.filename
            td { a worker.url, :href => worker.url }
          end
        end
      end
    end

    h3 "Upload a GTFS file"
    form :action => 'upload', :method => 'POST' do
      div :class => 'form-row' do
        label do
          span "URL of GTFS feed"
          input :name => 'url'
        end
      end
      div :class => 'form-row' do
        label do
          span "Transit Agency"
          input :name => 'agencyname'
        end
      end
      div :class => 'form-row' do
        label do
          span "City"
          input :name => 'city'
        end
      end
      button 'Upload!', :type => 'submit'
    end

    h3 "Uploaded GTFS files"
    ul do
      Dir.new(ENV['HOME'] + '/gtfs/').entries.select do |f|
        f[0] != '.'
      end.each do |file|
        li file
      end
    end
    
  end
end

require 'open-uri'
module GtfsUpload::Helpers
  
  class Worker
    def _outputdir_name(agencyname, city)
      return ENV['HOME'] + '/gtfs/'
    end

    def _file_name(agencyname, city)
      return city + '_' + agencyname + '.db'
    end
    
    attr_reader :url, :agencyname, :city, :outputdir, :filename, :status

    def initialize(url, agencyname, city)
      @agencyname = agencyname
      @city = city
      @outputdir = _outputdir_name(agencyname, city)
      @filename = _file_name(agencyname, city)
      @status = :idle
      @url = url
    end

    def fetch()
      @thread = Thread.new do
        begin
          wd = Dir.getwd
          @status = :started
          Dir.mktmpdir do |tmpdir|
            puts "downloading..."
            open(@url) do |f|
              @status = :downloaded
              system('unzip', f.path, '-d', tmpdir) or raise Exception.new("Unzip fail: #{$?}")
            end
            @status = :unzipped
            system(wd + '/gtfs-parse.py', tmpdir) or raise Exception.new("GTFS-parse fail: #{$?}")
            @status = :parsed
            # if outputdir doesn't exist, create it
            if not File.exist? @outputdir
              Dir.mkdir @outputdir
            end
            File.rename(tmpdir + '/gtfs.db', @outputdir + '/' + @filename)
            @status = :done
          end
        rescue Exception => e
          @status = :error
          puts e
        end
      end
    end

    def join()
      @thread.join
    end
  end
end
